# Volna: Music Feature Extraction and Similarity API

Volna is a project designed for extracting audio features, classifying genres, and finding similar music tracks. It provides a FastAPI backend for these functionalities, coupled with a simple web interface for interaction.

## Features

*   **Audio Feature Extraction:** Extracts various audio features from music files (e.g., BPM, RMS energy, spectral centroids, MFCCs).
*   **Genre Classification:** Utilizes a pre-trained model (MIT/ast-finetuned-audioset) to classify music genres.
*   **Similar Track Discovery:** Finds tracks similar to a given track based on combined audio and genre features using cosine similarity.
*   **FastAPI Backend:** A robust and scalable API for serving track data, similarity results, and managing listening history and playlists.
*   **Static File Serving:** Serves audio files directly via the FastAPI application.
*   **Duplicate Detection:** Basic detection to avoid processing the same track multiple times.

## Setup

### Prerequisites

*   Python 3.8+
*   `ffmpeg` (for `librosa` to load certain audio formats). Ensure `ffmpeg` is installed and available in your system's PATH.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/Volna.git
    cd Volna
    ```
    *(Replace `https://github.com/your-username/Volna.git` with your actual repository URL)*

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the root directory of the project. This file will hold your configurations.
    ```
    # --- General Configuration ---
    # Path to the SQLite database file
    DATABASE_URL=music_features.db

    # Folder to scan for music files (relative to project root)
    MUSIC_FOLDER=Yandex

    # --- FastAPI Configuration ---
    # Comma-separated list of allowed CORS origins for the FastAPI app
    CORS_ORIGINS=http://localhost:5174,http://127.0.0.1:5174

    # Cooldown period in seconds for certain API actions (e.g., listening history update)
    COOLDOWN_PERIOD_SECONDS=600

    # --- Model Configuration ---
    # Audio classification model device ('0' for GPU, 'cpu' for CPU)
    CLASSIFIER_DEVICE=0
    ```
    *   **`DATABASE_URL`**: The name of your SQLite database file.
    *   **`MUSIC_FOLDER`**: The directory (relative to the project root) where your music files are stored. The `scan.py` script will look here.
    *   **`CORS_ORIGINS`**: A comma-separated list of origins that are allowed to make requests to your FastAPI backend. Adjust these as needed for your frontend application.
    *   **`COOLDOWN_PERIOD_SECONDS`**: Adjust as needed.
    *   **`CLASSIFIER_DEVICE`**: Set to `0` for GPU (if available) or `cpu` for CPU-only processing.

5.  **Populate the Database:**
    Place your music files into the directory specified by `MUSIC_FOLDER` (e.g., `Yandex/` in the project root). Then, run the scanning script to extract features and populate the database:
    ```bash
    python scan.py
    ```
    This process might take a while depending on the number and size of your music files.

## Running the Application

1.  **Start the FastAPI server:**
    Navigate to the `fastapi` directory and run:
    ```bash
    cd fastapi
    uvicorn main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

2.  **Access the Web UI:**
    If you have a separate frontend application, configure it to connect to the FastAPI backend. You might need to serve the frontend application separately (e.g., using `npm run dev` for a React app).

## Important Notes

*   **Copyright:** This project *does not include any music files* due to copyright restrictions. You must provide your own music files.
*   **Database:** The `music_features.db` file (and any other `.db` files) should **not** be committed to version control, as it contains user-specific data and local file paths. It is already included in `.gitignore`.
*   **Model:** The genre classification model `MIT/ast-finetuned-audioset-10-10-0.4593` will be downloaded by the `transformers` library on first use.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
