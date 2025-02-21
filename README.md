# NutriTrack - Nutrition Tracking Application

A Flask-based web application for tracking daily nutrition, managing food intake, and setting dietary goals.

## Features

- User authentication and profile management
- Food tracking with USDA database integration
- Daily nutrition summary
- Customizable nutrition goals
- Recipe suggestions
- Responsive design using Bootstrap

## Tech Stack

- Backend: Flask, SQLAlchemy
- Database: PostgreSQL
- Frontend: HTML, CSS (Bootstrap), JavaScript
- APIs: USDA Food Data Central

## Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables in `.env`:
   ```
   SECRET_KEY=your-secret-key
   DATABASE_URL=your-database-url
   USDA_API_KEY=your-usda-api-key
   ```
4. Run the application:
   ```bash
   python app.py
   ```

## Deployment

This application is configured for deployment on Vercel with a PostgreSQL database.

## License

MIT