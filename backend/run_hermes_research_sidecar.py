from pathlib import Path

from app.services.hermes_research_sidecar import (
    create_hermes_research_sidecar_app,
    load_repo_dotenv_for_sidecar,
)

load_repo_dotenv_for_sidecar(Path(__file__))
app = create_hermes_research_sidecar_app()


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=8788,
        debug=False,
        threaded=True,
    )
