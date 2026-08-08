import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=False), override=False)

from app import create_app

app = create_app()

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('FLASK_PORT', 5000))
    # Disable the reloader to prevent the app from starting twice
    app.run(debug=debug, port=port, use_reloader=False)

