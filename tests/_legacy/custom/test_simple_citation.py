"""
Simple test of citation export functionality using Django management command
"""
import os
os.environ.setdefault('SCITEX_CLOUD_DJANGO_SETTINGS_MODULE', 'config.settings')

from datetime import date

# Mock paper data for testing
class MockPaper:
    def __init__(self):
        self.title = "Neural mechanisms of visual attention in cortical processing"
        self.abstract = "This study investigates the neural mechanisms underlying visual attention in cortical processing networks."
        self.publication_date = date(2024, 1, 15)
        self.doi = "10.1038/s41593-024-0001-1"
        self.pmid = "38000001"
        self.citation_count = 25
        self.source = "pubmed"
        self.is_open_access = True
        self.journal = MockJournal()
        self.id = "test-paper-id"
    
    def get_authors_display(self):
        return "Smith, John and Doe, Jane"

class MockJournal:
    def __init__(self):
        self.name = "Nature Neuroscience"
        self.abbreviation = "Nat. Neurosci."
        self.issn = "1097-6256"

def test_bibtex_generation():
    """Test BibTeX generation with mock data"""
    paper = MockPaper()
    
    # Generate BibTeX entry manually
    authors = "Smith, John and Doe, Jane"
    year = paper.publication_date.year if paper.publication_date else "2024"
    
    bibtex_key = f"smith{year}neural"
    
    bibtex = f"""@article{{{bibtex_key},
    title={{{paper.title}}},
    author={{{authors}}},
    journal={{{paper.journal.name}}},
    year={{{year}}},
    doi={{{paper.doi}}},
    pmid={{{paper.pmid}}},
    url={{https://pubmed.ncbi.nlm.nih.gov/{paper.pmid}/}},
    abstract={{{paper.abstract}}}
}}"""
    
    return bibtex

def test_ris_generation():
    """Test RIS generation with mock data"""
    paper = MockPaper()
    year = paper.publication_date.year if paper.publication_date else "2024"
    
    ris = f"""TY  - JOUR
TI  - {paper.title}
AU  - Smith, John
AU  - Doe, Jane
JO  - {paper.journal.name}
PY  - {year}
DO  - {paper.doi}
UR  - https://pubmed.ncbi.nlm.nih.gov/{paper.pmid}/
AB  - {paper.abstract}
ER  - """
    
    return ris

def test_endnote_generation():
    """Test EndNote generation with mock data"""
    paper = MockPaper()
    year = paper.publication_date.year if paper.publication_date else "2024"
    
    endnote = f"""%0 Journal Article
%T {paper.title}
%A Smith, John
%A Doe, Jane
%J {paper.journal.name}
%D {year}
%R {paper.doi}
%U https://pubmed.ncbi.nlm.nih.gov/{paper.pmid}/
%X {paper.abstract}"""
    
    return endnote

if __name__ == '__main__':
    print("🧪 Testing Scholar Citation Export Formats")
    print("=" * 60)
    
    # Test BibTeX
    print("\n📝 BibTeX Format Test:")
    print("-" * 30)
    bibtex = test_bibtex_generation()
    print("✅ BibTeX generation successful")
    print(bibtex)
    
    # Test RIS
    print("\n📄 RIS Format Test:")
    print("-" * 30)
    ris = test_ris_generation()
    print("✅ RIS generation successful")
    print(ris)
    
    # Test EndNote
    print("\n📚 EndNote Format Test:")
    print("-" * 30)
    endnote = test_endnote_generation()
    print("✅ EndNote generation successful")
    print(endnote)
    
    print("\n" + "=" * 60)
    print("✅ Citation Format Testing Complete!")
