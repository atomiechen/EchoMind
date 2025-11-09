# EchoMind

[CSCW Paper](https://dl.acm.org/doi/10.1145/3757587) | [Medium](https://medium.com/acm-cscw/how-did-we-get-here-keeping-real-time-discussions-focused-with-echomind-3abab96573ed)

Official code repository for our CSCW 2025 paper:

**EchoMind: Supporting Real-time Complex Problem Discussions through Human-AI Collaborative Facilitation**

The system generates real-time issue maps for ongoing conversations to facilitate complex problem discussions.
Code in this repository implements extra features beyond the paper:
- User & discussion management: multiple remote users can join the same discussion session.
- Post-discussion review with transcript, issue map, and recorded audio (if configured to do so).
- Internationalization (i18n) support.


## Video

<p align="center">
  <a href="https://www.youtube.com/watch?v=p9HmHKXj8G8" target="_blank">
    <img width="70%" alt="YouTube Video Thumbnail" src="https://github.com/user-attachments/assets/e86d3687-faa3-4b43-993b-cfcfa99e586d" />
  </a>
</p>


## Project Overview


The project is a full-stack web application with a Python backend and a React frontend. It is structured as follows:

- `backend`: A FastAPI server that handles API requests, manages real-time communication with SocketIO, and interacts with the database and AI models. It also serves the frontend static files if configured.
- `frontend`: A React single-page application (SPA) that provides the user interface.

<!-- - `data`: The folder that discussion data will be stored. The SQLite database file will also be created here. -->


## Setup

### Prerequisites

- [OpenAI API key(s)](https://platform.openai.com/api-keys), or other compatible LLM API keys.
- [FunASR](https://github.com/modelscope/FunASR) service URI for real-time speech recognition.
  - FunASR is open source and free to deploy its runtime service on your own server. Follow the [FunASR runtime guide](https://github.com/modelscope/FunASR/blob/main/runtime/readme.md), and check out the improved [startup scripts](https://gist.github.com/atomiechen/2deaf80dba21b4434ab21d6bf656fbca).
  - You can also use other ASR services by implementing a compatible asynchronous client in the backend.

### Backend Setup

Change to the `backend` directory (`cd backend`):

1. Install backend dependencies.

   (a) We use [uv](https://docs.astral.sh/uv/) to manage the Python virtual environment and dependencies. 

   - Create a virtual environment `.venv` and install the dependencies:

      ```sh
      uv sync
      ```

   - Then activate the virtual environment using `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows).

   (b) You can also use `pip` if you prefer (activate your virtual environment first).

   ```sh
   pip install -e .[dev]
   ```

2. Set up configuration.

   Copy the template configuration file to `config.yaml`.

   ```sh
   cp config.template.yaml config.yaml
   ```

   Then edit `config.yaml` to at least set up the OpenAI API key and the FunASR service URI.

### Frontend Setup

Change to the `frontend` directory (`cd frontend`).

1. Install frontend dependencies.

   ```sh
   # install from package-lock.json
   npm ci
   ```

2. Build the frontend static files for production.

   ```sh
   npm run build
   ```

## Running the Application

By default, the backend server will serve the frontend static files (`spa_path` configured in `config.yaml`).

Run the backend server in the background (`cd backend`):

```sh
# start server in the background
dmon start
# check server status
dmon status
# stop the background server
dmon stop
```

Or run it in the foreground:

```sh
dmon exec
```

Then, open your web browser and navigate to http://localhost:8000 to access the application.


> [!NOTE]
> [**dmon**](https://github.com/atomiechen/python-dmon) is a lightweight, cross-platform daemon manager that runs commands as background processes, *without* Docker. 
> It is already included in the backend dependencies.
> Feel free to use it and give it a star ⭐️!


## Development

### Running Frontend Separately

To run the frontend separately for development (`cd frontend`):

1. Copy the template environment file to `.env.development`.

   ```sh
   cp .env.development.template .env.development
   ```

   It sets the backend API URL (`VITE_API_BASE_URL=http://localhost:8000`) for development mode.

2. Start the frontend development server with hot-reload (HMR):

   ```sh
   npm run dev
   ```

   Then open your web browser and navigate to http://localhost:5173 to access the application.


### Generating API Client & Models

The API client code in `frontend/src/client` is generated from the OpenAPI specification provided by the FastAPI backend.
To regenerate the API client, run the following command in the `backend` directory:

```sh
bash ./scripts/gen_client.sh
```

SocketIO models in `frontend/src/lib/models.ts` are generated from the Pydantic models defined in the backend.
To regenerate them:

```sh
bash ./scripts/gen_models.sh
```

### Prompts

Prompt templates are stored as `.hprompt` files in the `backend/app/core/prompts` directory.

The human-friendly mark-up format is designed and consumed by [**HandyLLM**](https://github.com/atomiechen/HandyLLM), which is already included in the backend dependencies.
You can test and run prompts directly without running the whole application:

```sh
handyllm hprompt <your_prompt>.hprompt
```

For editor support with syntax highlighting, use the [VSCode extension](https://marketplace.visualstudio.com/items?itemName=atomiechen.handyllm) or [Sublime Text package](https://packagecontrol.io/packages/HandyLLM).

> [!NOTE]
> HandyLLM is for rapid prototyping of LLM applications.
> Feel free to give it a star ⭐️!


## Citation

If you find our work useful, or if you use the code or prompts from this repository, please cite our paper:

> Weihao Chen, Chun Yu, Yukun Wang, Meizhu Chen, Yipeng Xu, and Yuanchun Shi. 2025. EchoMind: Supporting Real-time Complex Problem Discussions through Human-AI Collaborative Facilitation. Proc. ACM Hum.-Comput. Interact. 9, 7, Article CSCW406 (November 2025), 38 pages. https://doi.org/10.1145/3757587

```bibtex
@article{chen_echomind_2025,
author = {Chen, Weihao and Yu, Chun and Wang, Yukun and Chen, Meizhu and Xu, Yipeng and Shi, Yuanchun},
title = {EchoMind: Supporting Real-time Complex Problem Discussions through Human-AI Collaborative Facilitation},
year = {2025},
issue_date = {November 2025},
publisher = {Association for Computing Machinery},
address = {New York, NY, USA},
volume = {9},
number = {7},
url = {https://doi.org/10.1145/3757587},
doi = {10.1145/3757587},
abstract = {Teams often engage in group discussions to leverage collective intelligence when solving complex problems. However, in real-time discussions, such as face-to-face meetings, participants frequently struggle with managing diverse perspectives and structuring content, which can lead to unproductive outcomes like forgetfulness and off-topic conversations. Through a formative study, we explores a human-AI collaborative facilitation approach, where AI assists in establishing a shared knowledge framework to provide a guiding foundation. We present EchoMind, a system that visualizes discussion knowledge through real-time issue mapping. EchoMind empowers participants to maintain focus on specific issues, review key ideas or thoughts, and collaboratively expand the discussion. The system leverages large language models (LLMs) to dynamically organize dialogues into nodes based on the current context recorded on the map. Our user study with four teams (N=16) reveals that EchoMind helps clarify discussion objectives, trace knowledge pathways, and enhance overall productivity. We also discuss the design implications for human-AI collaborative facilitation and the potential of shared knowledge visualization to transform group dynamics in future collaborations.},
journal = {Proc. ACM Hum.-Comput. Interact.},
month = oct,
articleno = {CSCW406},
numpages = {38},
keywords = {complex problems, group discussions, human-AI collaboration, issue mapping, large language models}
}
```
