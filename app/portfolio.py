import pandas as pd
import chromadb
import uuid
import os
import requests
import io


class Portfolio:
    def __init__(self, file_path=None):
        # Use provided file path or default
        if file_path is None:
            file_path = os.path.join(os.path.dirname(__file__), "resource", "my_portfolio.csv")
        
        self.file_path = file_path
        self.data = pd.read_csv(file_path)
        self.chroma_client = chromadb.PersistentClient('vectorstore')
        self.collection = self.chroma_client.get_or_create_collection(name="portfolio")

    @staticmethod
    def load_portfolio_from_source(source):
        """
        Load portfolio from different sources:
        - Local file path
        - URL to CSV
        - Pandas DataFrame
        """
        if isinstance(source, pd.DataFrame):
            return source
        
        # Check if source is a URL
        if source.startswith(('http://', 'https://')):
            try:
                response = requests.get(source)
                response.raise_for_status()
                return pd.read_csv(io.StringIO(response.text))
            except Exception as e:
                raise ValueError(f"Error loading portfolio from URL: {e}")
        
        # Assume local file path
        if not os.path.exists(source):
            raise FileNotFoundError(f"Portfolio file not found: {source}")
        
        return pd.read_csv(source)

    def load_collection(self, portfolio_data):
        """
        Load portfolio data into ChromaDB collection
        """
        # Clear existing collection
        if self.collection.count():
            self.collection.delete(ids=self.collection.get()['ids'])
        
        # Load portfolio data
        for _, row in portfolio_data.iterrows():
            self.collection.add(
                documents=row["Techstack"],
                metadatas={"links": row["Links"]},
                ids=[str(uuid.uuid4())]
            )

    def load_portfolio(self, custom_portfolio_source=None):
        """
        Load portfolio from custom source or default
        """
        try:
            # Use custom source if provided, otherwise use default
            if custom_portfolio_source:
                portfolio_data = self.load_portfolio_from_source(custom_portfolio_source)
            else:
                portfolio_data = self.data
            
            # Load into collection
            self.load_collection(portfolio_data)
        except Exception as e:
            # Fallback to default portfolio if custom source fails
            print(f"Error loading custom portfolio: {e}. Using default.")
            self.load_collection(self.data)

    def query_links(self, skills, n_results=2):
        """
        Query portfolio links based on skills
        """
        return self.collection.query(query_texts=skills, n_results=n_results).get('metadatas', [])
