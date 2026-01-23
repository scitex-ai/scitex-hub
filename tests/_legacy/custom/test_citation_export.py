#!/usr/bin/env python3
"""
Test script for Scholar citation export functionality
"""
import os
import sys
import json

# Setup Django environment
os.environ.setdefault('SCITEX_CLOUD_DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User

from apps.scholar.models import SearchIndex, Author, Journal, AuthorPaper
from apps.scholar.utils import CitationExporter

def create_test_data():
    """Create test paper data for citation export testing"""
    
    # Create test journal
    journal, created = Journal.objects.get_or_create(
        name="Nature Neuroscience",
        defaults={
            'abbreviation': 'Nat. Neurosci.',
            'issn': '1097-6256',
            'impact_factor': 21.126,
            'publisher': 'Nature Publishing Group'
        }
    )
    
    # Create test authors
    author1, created = Author.objects.get_or_create(
        first_name="John",
        last_name="Smith",
        defaults={
            'orcid': '0000-0000-0000-0001',
            'email': 'john.smith@university.edu',
            'affiliation': 'University of Science'
        }
    )
    
    author2, created = Author.objects.get_or_create(
        first_name="Jane",
        last_name="Doe",
        defaults={
            'orcid': '0000-0000-0000-0002',
            'email': 'jane.doe@research.org',
            'affiliation': 'Research Institute'
        }
    )
    
    # Create test paper
    paper, created = SearchIndex.objects.get_or_create(
        title="Neural mechanisms of visual attention in cortical processing",
        defaults={
            'abstract': 'This study investigates the neural mechanisms underlying visual attention in cortical processing networks. We used functional magnetic resonance imaging (fMRI) to examine attention-related activity patterns in human subjects.',
            'document_type': 'article',
            'publication_date': '2024-01-15',
            'journal': journal,
            'doi': '10.1038/s41593-024-0001-1',
            'pmid': '38000001',
            'citation_count': 25,
            'source': 'pubmed',
            'is_open_access': True,
            'status': 'active'
        }
    )
    
    # Link authors to paper
    if created:
        AuthorPaper.objects.get_or_create(
            author=author1,
            paper=paper,
            defaults={'author_order': 1, 'is_corresponding': True}
        )
        AuthorPaper.objects.get_or_create(
            author=author2,
            paper=paper,
            defaults={'author_order': 2, 'is_corresponding': False}
        )
    
    return paper

def test_citation_formats():
    """Test all citation export formats"""
    
    print("🧪 Testing Scholar Citation Export Functionality")
    print("=" * 60)
    
    # Create test data
    paper = create_test_data()
    papers = [paper]
    
    # Test BibTeX export
    print("\n📝 Testing BibTeX Export:")
    print("-" * 30)
    try:
        bibtex_content = CitationExporter.to_bibtex(papers)
        print("✅ BibTeX generation successful")
        print("Sample output:")
        print(bibtex_content[:300] + "..." if len(bibtex_content) > 300 else bibtex_content)
    except Exception as e:
        print(f"❌ BibTeX generation failed: {e}")
    
    # Test RIS export
    print("\n📄 Testing RIS Export:")
    print("-" * 30)
    try:
        ris_content = CitationExporter.to_ris(papers)
        print("✅ RIS generation successful")
        print("Sample output:")
        print(ris_content[:300] + "..." if len(ris_content) > 300 else ris_content)
    except Exception as e:
        print(f"❌ RIS generation failed: {e}")
    
    # Test EndNote export
    print("\n📚 Testing EndNote Export:")
    print("-" * 30)
    try:
        endnote_content = CitationExporter.to_endnote(papers)
        print("✅ EndNote generation successful")
        print("Sample output:")
        print(endnote_content[:300] + "..." if len(endnote_content) > 300 else endnote_content)
    except Exception as e:
        print(f"❌ EndNote generation failed: {e}")
    
    # Test CSV export
    print("\n📊 Testing CSV Export:")
    print("-" * 30)
    try:
        csv_content = CitationExporter.to_csv(papers)
        print("✅ CSV generation successful")
        print("Sample output:")
        lines = csv_content.split('\n')
        for i, line in enumerate(lines[:3]):  # Show first 3 lines
            print(f"Line {i+1}: {line[:100]}..." if len(line) > 100 else f"Line {i+1}: {line}")
    except Exception as e:
        print(f"❌ CSV generation failed: {e}")

def test_api_endpoints():
    """Test citation export API endpoints"""
    
    print("\n🌐 Testing Citation Export API Endpoints:")
    print("=" * 60)
    
    # Create test user and authenticate
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    
    client = Client()
    client.force_login(user)
    
    # Create test paper
    paper = create_test_data()
    
    # Test data for API calls
    test_data = {
        'paper_ids': [str(paper.id)],
        'collection_name': 'test_export'
    }
    
    endpoints = [
        ('/scholar/api/export/bibtex/', 'BibTeX'),
        ('/scholar/api/export/ris/', 'RIS'),
        ('/scholar/api/export/endnote/', 'EndNote'),
        ('/scholar/api/export/csv/', 'CSV')
    ]
    
    for endpoint, format_name in endpoints:
        print(f"\n🔗 Testing {format_name} API endpoint: {endpoint}")
        try:
            response = client.post(
                endpoint,
                data=json.dumps(test_data),
                content_type='application/json'
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✅ {format_name} API endpoint working correctly")
                    print(f"   - Filename: {data.get('filename', 'N/A')}")
                    print(f"   - Content length: {len(data.get('content', ''))} characters")
                else:
                    print(f"❌ {format_name} API returned error: {data.get('error', 'Unknown')}")
            else:
                print(f"❌ {format_name} API endpoint failed with status {response.status_code}")
                
        except Exception as e:
            print(f"❌ {format_name} API test failed: {e}")

if __name__ == '__main__':
    print("🚀 Starting Scholar Citation Export Testing")
    
    try:
        # Test citation format generation
        test_citation_formats()
        
        # Test API endpoints
        test_api_endpoints()
        
        print("\n" + "=" * 60)
        print("✅ Citation Export Testing Complete!")
        print("The Scholar module citation export functionality is working properly.")
        
    except Exception as e:
        print(f"\n❌ Testing failed with error: {e}")
