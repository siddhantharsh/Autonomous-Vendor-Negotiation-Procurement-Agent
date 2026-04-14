import os
import json
import zipfile
import tempfile
import shutil
import re
import hashlib
import requests
import chromadb
from chromadb.utils import embedding_functions

CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "procurement_products"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen3:0.5b"


def get_chroma_collection():
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def build_product_text(product):
    parts = []
    name = product.get("product_name", "")
    if name:
        parts.append(f"Product: {name}")
    price = product.get("price", "")
    price_unit = product.get("price_unit", "")
    if price and price not in ["Not found", "N/A", ""]:
        parts.append(f"Price: Rs {price} {price_unit}".strip())
    supplier = product.get("supplier_name", "")
    if supplier and supplier != "Not found":
        parts.append(f"Supplier: {supplier}")
    location = product.get("supplier_location", "")
    if location and location != "Not found":
        parts.append(f"Location: {location}")
    category = product.get("category", "")
    if category:
        parts.append(f"Category: {category}")
    specs = product.get("specifications", {})
    if specs and isinstance(specs, dict):
        spec_lines = [
            f"{k}: {v}" for k, v in list(specs.items())[:8] if k and v
        ]
        if spec_lines:
            parts.append("Specifications: " + "; ".join(spec_lines))
    rating = product.get("supplier_rating", "")
    if rating and rating != "Not found":
        parts.append(f"Rating: {rating}")
    trustseal = product.get("trustseal_verified", "")
    if trustseal and trustseal not in ["Not found", "Not verified"]:
        parts.append("TrustSEAL Verified")
    years = product.get("years_experience", "")
    if years and years != "Not found":
        parts.append(f"Experience: {years}")
    return ". ".join(parts)


def extract_filters_from_query(query_text):
    filters = {}
    price_patterns = [
        r"under\s*[₹rs.]?\s*(\d+)",
        r"below\s*[₹rs.]?\s*(\d+)",
        r"less\s+than\s*[₹rs.]?\s*(\d+)",
        r"[₹rs.]\s*(\d+)\s+or\s+less",
        r"max\s+(?:price\s+)?[₹rs.]?\s*(\d+)",
    ]
    for pattern in price_patterns:
        match = re.search(pattern, query_text, re.IGNORECASE)
        if match:
            filters["max_price"] = int(match.group(1))
            break
    location_match = re.search(
        r"(?:from|in|at|near)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", query_text
    )
    if location_match:
        filters["location"] = location_match.group(1).strip()
    return filters


def apply_filters(results, filters):
    if not filters:
        return results
    filtered = []
    for result in results:
        metadata = result.get("metadata", {})
        if "max_price" in filters:
            try:
                price_str = metadata.get("price", "")
                if price_str and price_str not in ["Not found", "N/A", ""]:
                    price_val = float(re.sub(r"[^\d.]", "", price_str))
                    if price_val > filters["max_price"]:
                        continue
            except (ValueError, TypeError):
                pass
        if "location" in filters:
            loc = metadata.get("supplier_location", "").lower()
            if filters["location"].lower() not in loc:
                continue
        filtered.append(result)
    return filtered


def ollama_available():
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def query_ollama(prompt):
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        return ""
    except Exception:
        return ""


def build_database_from_zip(zip_path, progress_callback=None):
    collection = get_chroma_collection()
    temp_dir = tempfile.mkdtemp(prefix="rag_extract_")
    products_indexed = 0
    products_skipped = 0
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(temp_dir)

        json_files = [f for f in os.listdir(temp_dir) if f.endswith(".json")]
        total = len(json_files)

        for i, filename in enumerate(json_files):
            filepath = os.path.join(temp_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    product = json.load(f)

                doc_id = hashlib.md5(
                    product.get("URL", filename).encode()
                ).hexdigest()

                existing = collection.get(ids=[doc_id])
                if existing and existing.get("ids") and len(existing["ids"]) > 0:
                    products_skipped += 1
                    if progress_callback:
                        progress_callback(i + 1, total, filename, skipped=True)
                    continue

                text = build_product_text(product)
                metadata = {
                    "product_name": str(product.get("product_name", ""))[:500],
                    "price": str(product.get("price", ""))[:100],
                    "price_unit": str(product.get("price_unit", ""))[:100],
                    "supplier_name": str(product.get("supplier_name", ""))[:200],
                    "supplier_location": str(product.get("supplier_location", ""))[:200],
                    "category": str(product.get("category", ""))[:200],
                    "supplier_rating": str(product.get("supplier_rating", ""))[:200],
                    "trustseal_verified": str(product.get("trustseal_verified", ""))[:100],
                    "url": str(product.get("URL", ""))[:500],
                }
                collection.add(ids=[doc_id], documents=[text], metadatas=[metadata])
                products_indexed += 1
                if progress_callback:
                    progress_callback(i + 1, total, filename, skipped=False)
            except Exception as e:
                print(f"Error processing {filename}: {e}")

        return {
            "success": True,
            "indexed": products_indexed,
            "skipped": products_skipped,
            "total_in_db": collection.count(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "indexed": 0, "skipped": 0}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def query_products(query_text, n_results=5):
    collection = get_chroma_collection()
    if collection.count() == 0:
        return {
            "error": "Database is empty. Please build the database first.",
            "results": [],
            "llm_answer": "",
            "filters_extracted": {},
            "total_in_db": 0,
        }
    filters = extract_filters_from_query(query_text)
    search_n = min(n_results * 3, 20)
    try:
        results = collection.query(query_texts=[query_text], n_results=search_n)
    except Exception as e:
        return {
            "error": f"Query failed: {e}",
            "results": [],
            "llm_answer": "",
            "filters_extracted": filters,
            "total_in_db": collection.count(),
        }

    formatted_results = []
    for i, (doc, metadata, distance) in enumerate(
        zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
    ):
        formatted_results.append(
            {
                "rank": i + 1,
                "similarity": round(1 - distance, 3),
                "document": doc,
                "metadata": metadata,
            }
        )

    filtered_results = apply_filters(formatted_results, filters)[:n_results]

    llm_answer = ""
    if ollama_available() and filtered_results:
        products_context = "\n\n".join(
            [f"Product {r['rank']}: {r['document']}" for r in filtered_results[:5]]
        )
        prompt = (
            f"You are a procurement assistant. Based on the following product data, "
            f"answer the user's query concisely.\n\n"
            f"Query: {query_text}\n\n"
            f"Product Data:\n{products_context}\n\n"
            f"Provide a helpful, concise answer summarizing the most relevant products "
            f"and any insights about pricing, suppliers, or specifications."
        )
        llm_answer = query_ollama(prompt)

    return {
        "query": query_text,
        "filters_extracted": filters,
        "results": filtered_results,
        "llm_answer": llm_answer,
        "total_in_db": collection.count(),
    }


def get_database_stats():
    try:
        collection = get_chroma_collection()
        return {"count": collection.count(), "exists": True, "path": CHROMA_DB_PATH}
    except Exception:
        return {"count": 0, "exists": False, "path": CHROMA_DB_PATH}


def clear_database():
    try:
        if os.path.exists(CHROMA_DB_PATH):
            shutil.rmtree(CHROMA_DB_PATH)
        return True
    except Exception:
        return False


def main():
    print("=" * 60)
    print("  Autonomous Procurement Agent — RAG Query Engine")
    print("=" * 60)

    stats = get_database_stats()
    print(f"\nDatabase: {stats['count']} products indexed at '{stats['path']}'")

    if stats["count"] == 0:
        zip_path = input("\nPath to scraped ZIP file: ").strip().strip('"')
        if not os.path.exists(zip_path):
            print(f"File not found: {zip_path}")
            return

        print("\nBuilding database, this may take a few minutes...")

        def print_progress(current, total, filename, skipped=False):
            status = "skipped" if skipped else "indexed"
            print(f"  [{current}/{total}] {filename[:40]} — {status}")

        result = build_database_from_zip(zip_path, progress_callback=print_progress)
        if result["success"]:
            print(
                f"\nDone. Indexed {result['indexed']} products "
                f"({result['skipped']} duplicates skipped). "
                f"Total in DB: {result['total_in_db']}"
            )
        else:
            print(f"\nFailed to build database: {result.get('error')}")
            return

    print("\n" + "=" * 60)
    print("  Interactive Query Session  (type 'quit' to exit)")
    print("=" * 60)

    while True:
        try:
            query = input("\nQuery > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        if query.lower() in ("q", "quit", "exit"):
            print("Goodbye.")
            break
        if not query:
            continue

        result = query_products(query)

        if "error" in result:
            print(f"Error: {result['error']}")
            continue

        if result.get("filters_extracted"):
            print(f"Detected filters: {result['filters_extracted']}")

        print(f"\nTop {len(result['results'])} results:\n")
        for r in result["results"]:
            meta = r["metadata"]
            print(f"  [{r['rank']}] {meta.get('product_name', 'Unknown')}  "
                  f"(similarity: {r['similarity']})")
            if meta.get("price") not in ["Not found", "N/A", ""]:
                print(f"       Price: Rs {meta['price']} {meta.get('price_unit', '')}")
            if meta.get("supplier_name", "Not found") != "Not found":
                print(f"       Supplier: {meta['supplier_name']} "
                      f"({meta.get('supplier_location', '')})")
            if meta.get("url"):
                print(f"       URL: {meta['url']}")
            print()

        if result.get("llm_answer"):
            print("-" * 60)
            print("AI Summary:")
            print(result["llm_answer"])
            print("-" * 60)


if __name__ == "__main__":
    main()
