## Setup

### Prerequisites

- Python 3.7 or higher
- `pip` (Python package installer)

### Creating a Virtual Environment

Before running the app, it's recommended to create a virtual environment. This will help isolate the dependencies for this project from your global Python environment.

#### For Windows:

1. Open Command Prompt or PowerShell.
2. Navigate to your project directory.
3. Run the following command to create a virtual environment named `.venv`:

   ```bash
   python -m venv .venv
   ```

### Activating the Virtual Environment

### For Windows:

    .venv\Scripts\activate

### For macOS/Linux:

    source .venv/bin/activate

### Installing Dependencies

    pip install -r requirements.txt

### Running the App

    uvicorn main:app --reload
