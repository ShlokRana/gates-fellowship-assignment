"""Build a FAISS vector store from the PDFs in data/."""
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()


def build_vectorstore(data_dir: Path, out_dir: Path) -> None:
    pdf_paths = sorted(Path(data_dir).glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDFs found in {data_dir}")

    docs = []
    for pdf_path in pdf_paths:
        loader = PyPDFLoader(str(pdf_path))
        docs.extend(loader.load())

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    store = FAISS.from_documents(chunks, embeddings)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    store.save_local(str(out_dir))
    print(f"Indexed {len(chunks)} chunks from {len(pdf_paths)} PDFs → {out_dir}")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    build_vectorstore(repo_root / "data", repo_root / "vectorstore")
