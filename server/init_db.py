from models.database import Base, engine, SessionLocal
from dotenv import load_dotenv
import sys
import argparse
from sqlalchemy.schema import DropTable
from sqlalchemy.ext.compiler import compiles
from sqlalchemy import inspect

def table_exists(table_name):
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def init_database(force=False):
    """Initialize the database by dropping and recreating all tables if force=True,
    or just creating missing tables if force=False."""
    # Load environment variables
    load_dotenv()
    
    # Add CASCADE support for dropping tables with dependencies
    @compiles(DropTable, "postgresql")
    def _compile_drop_table(element, compiler, **kwargs):
        return compiler.visit_drop_table(element) + " CASCADE"
    
    # Check if tables already exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # If we have some tables and not in force mode, just ensure all tables exist
    if existing_tables and not force:
        print("\n🔄 Checking database structure...")
        try:
            # This will create any missing tables without dropping existing ones
            Base.metadata.create_all(bind=engine)
            print(f"✅ Database structure verified - found {len(existing_tables)} existing tables")
            print("✅ Added any missing tables")
            return
        except Exception as e:
            print(f"\n⚠️ Error checking database structure: {str(e)}")
            print("Continuing with normal initialization...")
    
    # Only proceed with full initialization if force=True or no tables exist
    if force:
        print("\n🔄 Force mode: Initializing database (all existing data will be removed)...")
    else:
        print("\n🔄 No existing tables found, initializing database...")
        
    try:
        if force or not existing_tables:
            print("🔄 Dropping all existing tables...")
            Base.metadata.drop_all(bind=engine)
            print("✅ All tables dropped successfully")
        
        print("🔄 Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully")
        
        print("🎉 Database initialized successfully!")
    except Exception as e:
        print(f"\n❌ Error initializing database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the TradeMind database")
    parser.add_argument('-f', '--force', action='store_true', 
                        help='Force initialization with dropping all existing tables')
    args = parser.parse_args()
    
    # Only use force if explicitly requested
    init_database(force=args.force)
    
    print("\nYou can now start the application with:")
    print("python main.py")