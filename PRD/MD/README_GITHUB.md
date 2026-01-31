# School Catchment Search - GitHub Repository Structure

A Flask web application for searching school catchments and addresses using GNAF and school profile data.

## 📁 Repository Structure

```
school-catchment-search/
│
├── webapp/                          # Main Flask application
│   ├── app.py                       # Flask application entry point
│   ├── models.py                    # Database models
│   ├── __init__.py                  # Package initialization
│   ├── templates/                   # HTML templates
│   │   ├── school_search.html      # School search interface
│   │   ├── address_search.html     # Address search interface
│   │   └── base.html               # Base template
│   └── static/                      # Static assets
│       ├── css/
│       │   └── style.css            # Main stylesheet
│       ├── js/
│       │   ├── school.js            # School search logic
│       │   ├── address.js           # Address search logic
│       │   └── main.js              # Common utilities
│       └── images/
│
├── database/                        # Database setup and migrations
│   ├── setup/
│   │   ├── setup_gnaf_database.sql
│   │   ├── create_school_lookup_table.sql
│   │   ├── create_school_profile_2025_table.sql
│   │   └── create_spatial_indexes.sql
│   ├── migrations/                  # SQL migration files
│   └── queries/                     # Useful queries
│
├── scripts/                         # Python utility scripts
│   ├── load_gnaf_data.py           # Load GNAF data into database
│   ├── load_school_catchments.py   # Load school catchment data
│   ├── load_school_profiles.py     # Load school profile data
│   ├── create_school_lookup.py     # Create lookup table
│   ├── geocode_schools_osm.py      # Geocode schools using OSM
│   └── data_validation/            # Data validation scripts
│
├── docs/                            # Documentation
│   ├── DEPLOYMENT_GUIDE.md         # Deployment instructions
│   ├── GNAF_SETUP_GUIDE.md         # GNAF setup guide
│   ├── SCHOOL_CATCHMENT_GUIDE.md  # School catchment guide
│   ├── API_DOCUMENTATION.md        # API endpoint documentation
│   ├── DATABASE_SCHEMA.md          # Database schema documentation
│   └── ARCHITECTURE.md             # System architecture
│
├── tests/                           # Unit and integration tests
│   ├── test_api.py                 # API endpoint tests
│   ├── test_models.py              # Model tests
│   └── fixtures/                   # Test fixtures
│
├── config/                          # Configuration files
│   ├── settings.py                 # Application settings
│   ├── database.conf.example       # Database config template
│   └── logging.conf                # Logging configuration
│
├── data/                            # Data directory
│   ├── samples/                    # Sample data files
│   ├── exports/                    # Exported data
│   └── .gitkeep
│
├── .env.example                    # Environment variables template
├── .gitignore                      # Git ignore rules
├── requirements.txt                # Python dependencies
├── setup.py                        # Package setup file
├── Dockerfile                      # Docker configuration
├── docker-compose.yml              # Docker compose configuration
├── LICENSE                         # License file
└── README.md                       # Main README file

```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- PostGIS extension
- pip or conda

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/school-catchment-search.git
cd school-catchment-search
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your database credentials
```

5. **Setup database**
```bash
# Run setup scripts in order
psql -U postgres -f database/setup/setup_gnaf_database.sql
psql -U postgres -d gnaf_db -f database/setup/create_school_lookup_table.sql
psql -U postgres -d gnaf_db -f database/setup/create_spatial_indexes.sql
```

6. **Load data**
```bash
# Load GNAF data (large dataset)
python scripts/load_gnaf_data.py

# Load school catchment data
python scripts/load_school_catchments.py

# Load school profiles
python scripts/load_school_profiles.py
```

7. **Run application**
```bash
cd webapp
python app.py
```

Visit `http://localhost:5000` in your browser.

## 📋 Features

- **School Search**: Find schools by name with autocomplete
- **Catchment Boundary**: View school catchment areas on map
- **Address Lookup**: Search addresses within school catchments
- **ICSEA Scores**: View school ICSEA scores and percentiles
- **School Information**: Access school profiles and contact details
- **Geographic Visualization**: Interactive maps with boundaries

## 🔌 API Endpoints

### School Endpoints
- `GET /api/autocomplete/schools?q=<query>` - School autocomplete
- `GET /api/school/<school_id>/info` - Get school information
- `GET /api/school/<school_id>/boundary` - Get catchment boundary
- `GET /api/school/<school_id>/addresses` - Get addresses in catchment

### Address Endpoints
- `GET /api/address/search?street=<street>&suburb=<suburb>` - Search addresses
- `GET /api/autocomplete/streets?q=<query>` - Street autocomplete
- `GET /api/autocomplete/suburbs?q=<query>` - Suburb autocomplete

## 📊 Database Schema

### Main Tables
- `gnaf.address_detail` - Address details
- `gnaf.school_catchments` - School catchment data
- `gnaf.school_profile_2025` - School profile information
- `gnaf.school_type_lookup` - School type lookup table
- `public.school_catchments_primary` - Primary school year levels
- `public.school_catchments_secondary` - Secondary school year levels

See `docs/DATABASE_SCHEMA.md` for complete schema documentation.

## 🔒 Security

- Uses environment variables for sensitive data
- SQL parameterized queries to prevent injection
- HTTPS recommended for production
- Database user should have minimal required permissions

## 📝 Configuration

### Environment Variables (.env)
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gnaf_db
DB_USER=postgres
DB_PASSWORD=your_password
SECRET_KEY=your_secret_key
DEBUG=False
```

## 🐳 Docker Deployment

```bash
# Build image
docker-compose build

# Run containers
docker-compose up -d

# Access at http://localhost:5000
```

## 📚 Documentation

- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [GNAF Setup Guide](docs/GNAF_SETUP_GUIDE.md)
- [School Catchment Guide](docs/SCHOOL_CATCHMENT_GUIDE.md)
- [API Documentation](docs/API_DOCUMENTATION.md)
- [Database Schema](docs/DATABASE_SCHEMA.md)

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=webapp tests/
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 👥 Authors

- Your Name - Initial work

## 🙏 Acknowledgments

- GNAF (Geospatial Information Register)
- DataVic School Zones 2024
- NSW Department of Education

## 📞 Support

For issues and questions, please open an issue on GitHub.

## 🗺️ Data Sources

- GNAF (Address data): https://data.gov.au/dataset/psma-gnaf
- School Catchments: https://discover.data.vic.gov.au/dataset/school-zones
- School Profiles: NSW and Victorian education departments
