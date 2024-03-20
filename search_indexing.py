import PyPDF2
import requests
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders.pdf import PyPDFium2Loader
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from constants import chunk_size, chunk_overlap, number_snippets_to_retrieve

def download_and_index_pdf(filepaths: list[str]) -> FAISS:
    """
    Download and index a list of PDFs based on the filepaths
    """

    def __update_metadata(pages, filepath):
        """
        Add to the document metadata the title and original filepath
        """
        for page in pages:
            try:
                with open(filepath, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    title = pdf_reader.metadata.title if '/Title' in pdf_reader.metadata else ""
                    page.metadata['source'] = filepath
                    page.metadata['title'] = title
            except Exception as e:
                print(f"Error while processing PDF from {filepath}: {e}")

        return pages

    all_pages = []
    for filepath in filepaths:
        print("in seaaaaaaaaaaaaaaarch", filepath)
        loader = PyPDFium2Loader(filepath)
        splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        pages = loader.load_and_split(splitter)
        print(pages)
        pages = __update_metadata(pages, filepath)
        all_pages += pages

    faiss_index = FAISS.from_documents(all_pages, OpenAIEmbeddings())

    return faiss_index

def search_faiss_index(faiss_index: FAISS, query: str, top_k: int = number_snippets_to_retrieve) -> list:
    """
    Search a FAISS index, using the passed query
    """

    docs = faiss_index.similarity_search(query, k=top_k)

    return docs
