# School Catchment Search

A Flask web application for searching school catchments and addresses using GNAF (Geospatial Information Register) and school profile data. Features interactive maps, address lookups, ICSEA scores, and school information.

## 🎯 Features

- **School Search** - Find schools by name with autocomplete suggestions
- **Catchment Boundary Visualization** - Interactive maps showing school catchment areas
- **Address Lookup** - Search specific addresses within school catchments
- **ICSEA Scores** - View Index of Community Socio-Educational Advantage scores and percentiles
- **School Information** - Access comprehensive school profiles and contact details
- **Geographic Data** - Real-time geospatial queries using PostGIS
- **Responsive Design** - Mobile-friendly web interface

## 🚀 Quick Start

### Requirements
- Python 3.8+
- PostgreSQL 12+ with PostGIS extension
- pip or conda

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/school-catchment-search.git
cd school-catchment-search

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Setup database
psql -U postgres -f database/setup/setup_gnaf_database.sql
psql -U postgres -d gnaf_db -f database/setup/create_school_lookup_table.sql

# Load data
python scripts/load_gnaf_data.py
python scripts/load_school_catchments.py

# Run application
cd webapp
python app.py
```

Visit `http://localhost:5000` in your browser.

## 🐳 Docker Setup

```bash
# Build and run with Docker Compose
docker-compose up -d

# Access at http://localhost:5000
```

## 📖 Documentation

- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) - Production deployment instructions
- [GNAF Setup Guide](docs/GNAF_SETUP_GUIDE.md) - Data source setup
- [API Documentation](docs/API_DOCUMENTATION.md) - REST API reference
- [Database Schema](docs/DATABASE_SCHEMA.md) - Data model documentation
- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions

## 🔌 API Endpoints

### School Endpoints
```
GET /api/autocomplete/schools?q=<query>          # Search schools
GET /api/school/<school_id>/info                # Get school details
GET /api/school/<school_id>/boundary            # Get catchment boundary
GET /api/school/<school_id>/addresses           # Get addresses in catchment
```

### Address Endpoints
```
GET /api/address/search?street=<street>&suburb=<suburb>
GET /api/autocomplete/streets?q=<query>
GET /api/autocomplete/suburbs?q=<query>
```

[Full API Documentation](docs/API_DOCUMENTATION.md)

## 💾 Database Tables

- `gnaf.address_detail` - Address information
- `gnaf.school_catchments` - School catchment boundaries
- `gnaf.school_profile_2025` - School profile data with ICSEA
- `gnaf.school_type_lookup` - School type and profile mapping
- `public.school_catchments_primary` - Primary school data
- `public.school_catchments_secondary` - Secondary school data

[Full Schema Documentation](docs/DATABASE_SCHEMA.md)

## 📁 Project Structure

```
school-catchment-search/
├── webapp/              # Flask application
├── config/              # Configuration
├── scripts/             # Utility scripts
├── database/            # Database setup
├── tests/               # Test files
├── docs/                # Documentation
├── Dockerfile           # Docker config
├── docker-compose.yml   # Docker Compose
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=webapp tests/

# Run specific test
pytest tests/test_api.py
```

## 🔒 Security

- Environment variables for sensitive data (use `.env`)
- Parameterized SQL queries to prevent injection
- User authentication system
- HTTPS recommended for production

## 📝 Configuration

Environment variables (see `.env.example`):
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gnaf_db
DB_USER=postgres
DB_PASSWORD=your_password
SECRET_KEY=your_secret_key
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for detailed guidelines.

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 👥 Authors

- Your Name - Initial work

## 🙏 Acknowledgments

- GNAF (Geospatial Information Register)
- DataVic School Zones
- NSW & Victorian Education Departments

## 📊 Data Sources

- **GNAF**: https://data.gov.au/dataset/psma-gnaf
- **School Zones**: https://discover.data.vic.gov.au/dataset/school-zones
- **School Profiles**: NSW and Victorian education data

## 📞 Support

For issues and questions:
- Open an [issue on GitHub](https://github.com/yourusername/school-catchment-search/issues)
- Check [existing documentation](docs/)

## 🗺️ Roadmap

- [ ] Advanced filtering options
- [ ] Export functionality (CSV, JSON)
- [ ] Performance optimizations
- [ ] Mobile app
- [ ] API rate limiting
- [ ] Webhook support

---

**Status**: Active Development | **Version**: 1.0.0 | **Last Updated**: January 2026
