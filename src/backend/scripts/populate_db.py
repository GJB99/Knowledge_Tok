import asyncio
import arxiv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use relative imports instead
from models import Content, Base
from database import DATABASE_URL, ARTICLES_DATABASE_URL

# Complete arXiv categories taxonomy
ARXIV_CATEGORIES = {
    'astro-ph': [
        'GA',  # Astrophysics of Galaxies
        'CO',  # Cosmology and Nongalactic Astrophysics
        'EP',  # Earth and Planetary Astrophysics
        'HE',  # High Energy Astrophysical Phenomena
        'IM',  # Instrumentation and Methods for Astrophysics
        'SR',  # Solar and Stellar Astrophysics
    ],
    'cond-mat': [
        'dis-nn',     # Disordered Systems and Neural Networks
        'mes-hall',   # Mesoscale and Nanoscale Physics
        'mtrl-sci',   # Materials Science
        'other',      # Other Condensed Matter
        'quant-gas',  # Quantum Gases
        'soft',       # Soft Condensed Matter
        'stat-mech',  # Statistical Mechanics
        'str-el',     # Strongly Correlated Electrons
        'supr-con',   # Superconductivity
    ],
    'cs': [
        'AI',  # Artificial Intelligence
        'AR',  # Hardware Architecture
        'CC',  # Computational Complexity
        'CE',  # Computational Engineering, Finance, and Science
        'CG',  # Computational Geometry
        'CL',  # Computation and Language
        'CR',  # Cryptography and Security
        'CV',  # Computer Vision and Pattern Recognition
        'CY',  # Computers and Society
        'DB',  # Databases
        'DC',  # Distributed, Parallel, and Cluster Computing
        'DL',  # Digital Libraries
        'DM',  # Discrete Mathematics
        'DS',  # Data Structures and Algorithms
        'ET',  # Emerging Technologies
        'FL',  # Formal Languages and Automata Theory
        'GL',  # General Literature
        'GR',  # Graphics
        'GT',  # Computer Science and Game Theory
        'HC',  # Human-Computer Interaction
        'IR',  # Information Retrieval
        'IT',  # Information Theory
        'LG',  # Machine Learning
        'LO',  # Logic in Computer Science
        'MA',  # Multiagent Systems
        'MM',  # Multimedia
        'MS',  # Mathematical Software
        'NA',  # Numerical Analysis
        'NE',  # Neural and Evolutionary Computing
        'NI',  # Networking and Internet Architecture
        'OH',  # Other Computer Science
        'OS',  # Operating Systems
        'PF',  # Performance
        'PL',  # Programming Languages
        'RO',  # Robotics
        'SC',  # Symbolic Computation
        'SD',  # Sound
        'SE',  # Software Engineering
        'SI',  # Social and Information Networks
        'SY',  # Systems and Control
    ],
    'econ': [
        'EM',  # Econometrics
        'GN',  # General Economics
        'TH',  # Theoretical Economics
    ],
    'eess': [
        'AS',  # Audio and Speech Processing
        'IV',  # Image and Video Processing
        'SP',  # Signal Processing
        'SY',  # Systems and Control
    ],
    'gr-qc': [],     # General Relativity and Quantum Cosmology
    'hep-ex': [],    # High Energy Physics - Experiment
    'hep-lat': [],   # High Energy Physics - Lattice
    'hep-ph': [],    # High Energy Physics - Phenomenology
    'hep-th': [],    # High Energy Physics - Theory
    'math': [
        'AC',  # Commutative Algebra
        'AG',  # Algebraic Geometry
        'AP',  # Analysis of PDEs
        'AT',  # Algebraic Topology
        'CA',  # Classical Analysis and ODEs
        'CO',  # Combinatorics
        'CT',  # Category Theory
        'CV',  # Complex Variables
        'DG',  # Differential Geometry
        'DS',  # Dynamical Systems
        'FA',  # Functional Analysis
        'GM',  # General Mathematics
        'GN',  # General Topology
        'GR',  # Group Theory
        'GT',  # Geometric Topology
        'HO',  # History and Overview
        'IT',  # Information Theory
        'KT',  # K-Theory and Homology
        'LO',  # Logic
        'MG',  # Metric Geometry
        'MP',  # Mathematical Physics
        'NA',  # Numerical Analysis
        'NT',  # Number Theory
        'OA',  # Operator Algebras
        'OC',  # Optimization and Control
        'PR',  # Probability
        'QA',  # Quantum Algebra
        'RA',  # Rings and Algebras
        'RT',  # Representation Theory
        'SG',  # Symplectic Geometry
        'SP',  # Spectral Theory
        'ST',  # Statistics Theory
    ],
    'math-ph': [],   # Mathematical Physics
    'nlin': [
        'AO',  # Adaptation and Self-Organizing Systems
        'CD',  # Chaotic Dynamics
        'CG',  # Cellular Automata and Lattice Gases
        'PS',  # Pattern Formation and Solitons
        'SI',  # Exactly Solvable and Integrable Systems
    ],
    'nucl-ex': [],   # Nuclear Experiment
    'nucl-th': [],   # Nuclear Theory
    'physics': [
        'acc-ph',     # Accelerator Physics
        'ao-ph',      # Atmospheric and Oceanic Physics
        'app-ph',     # Applied Physics
        'atm-clus',   # Atomic and Molecular Clusters
        'atom-ph',    # Atomic Physics
        'bio-ph',     # Biological Physics
        'chem-ph',    # Chemical Physics
        'class-ph',   # Classical Physics
        'comp-ph',    # Computational Physics
        'data-an',    # Data Analysis, Statistics and Probability
        'ed-ph',      # Physics Education
        'flu-dyn',    # Fluid Dynamics
        'gen-ph',     # General Physics
        'geo-ph',     # Geophysics
        'hist-ph',    # History and Philosophy of Physics
        'ins-det',    # Instrumentation and Detectors
        'med-ph',     # Medical Physics
        'optics',     # Optics
        'plasm-ph',   # Plasma Physics
        'pop-ph',     # Popular Physics
        'soc-ph',     # Physics and Society
        'space-ph',   # Space Physics
    ],
    'q-bio': [
        'BM',  # Biomolecules
        'CB',  # Cell Behavior
        'GN',  # Genomics
        'MN',  # Molecular Networks
        'NC',  # Neurons and Cognition
        'OT',  # Other Quantitative Biology
        'PE',  # Populations and Evolution
        'QM',  # Quantitative Methods
        'SC',  # Subcellular Processes
        'TO',  # Tissues and Organs
    ],
    'q-fin': [
        'CP',  # Computational Finance
        'EC',  # Economics
        'GN',  # General Finance
        'MF',  # Mathematical Finance
        'PM',  # Portfolio Management
        'PR',  # Pricing of Securities
        'RM',  # Risk Management
        'ST',  # Statistical Finance
        'TR',  # Trading and Market Microstructure
    ],
    'quant-ph': [],  # Quantum Physics
    'stat': [
        'AP',  # Applications
        'CO',  # Computation
        'ME',  # Methodology
        'ML',  # Machine Learning
        'OT',  # Other Statistics
        'TH',  # Statistics Theory
    ]
}

async def fetch_arxiv_papers(max_results=100):
    client = arxiv.Client()
    # Use UTC timezone for consistency with arXiv's dates
    date_filter = datetime.now().astimezone().replace(microsecond=0) - timedelta(days=300)
    
    # First, get all existing paper IDs from the database
    engine = create_async_engine(ARTICLES_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        existing_papers_query = select(Content.external_id)
        result = await session.execute(existing_papers_query)
        existing_paper_ids = {paper[0] for paper in result.fetchall()}
    
    papers = []
    for main_cat, subcats in ARXIV_CATEGORIES.items():
        for subcat in subcats:
            category = f"{main_cat}.{subcat}" if main_cat != subcat else main_cat
            search = arxiv.Search(
                query=f"cat:{category}",
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )
            
            results = list(client.results(search))
            for paper in results:
                # Skip if paper already exists in database
                if paper.entry_id in existing_paper_ids:
                    print(f"Skipping existing paper: {paper.title}")
                    continue
                    
                # Both dates are now timezone-aware for comparison
                if paper.published > date_filter:
                    papers.append({
                        'title': paper.title,
                        'abstract': paper.summary,
                        'url': paper.pdf_url,
                        'external_id': paper.entry_id,
                        'source': 'arxiv',
                        'published_date': paper.published,
                        'paper_metadata': {
                            'authors': [author.name for author in paper.authors],
                            'categories': [cat for cat in paper.categories],
                            'paper_id': paper.entry_id.split('/')[-1],
                            'published_date': paper.published.isoformat()
                        }
                    })
            print(f"Fetched {len(results)} new papers from {category}")
    
    return papers

async def store_papers(papers):
    engine = create_async_engine(ARTICLES_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        for paper in papers:
            existing = await session.execute(
                select(Content).where(Content.external_id == paper['external_id'])
            )
            if not existing.scalar_one_or_none():
                content = Content(
                    title=paper['title'],
                    abstract=paper['abstract'],
                    url=paper['url'],
                    external_id=paper['external_id'],
                    source=paper['source'],
                    published_date=paper['published_date'],
                    paper_metadata=paper['paper_metadata']
                )
                session.add(content)
        
        await session.commit()

async def main():
    papers = await fetch_arxiv_papers()
    print(f"Fetched {len(papers)} papers")
    await store_papers(papers)
    print("Database population complete!")

if __name__ == "__main__":
    asyncio.run(main()) 