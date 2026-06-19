# Contributing to Opportunity AI Engine

Thank you for your interest in contributing to the **Opportunity AI Engine**! We welcome contributions from developers, designers, writers, and security analysts of all backgrounds. 

This document outlines the guidelines and best practices for setting up the environment, writing code, and submitting changes.

---

## 1. Code of Conduct
By participating in this project, you agree to abide by our Code of Conduct:
- Be respectful, constructive, and welcoming.
- Focus on collaboration and improving the software for everyone.
- Report any harassment or inappropriate behavior to the maintainers.

---

## 2. Local Development Setup

To run and test the codebase on your local machine:

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### Backend Setup
1. Navigate to the project directory:
   ```bash
   cd opportunity-ai-engine
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. Copy the environment template and configure local variables:
   ```bash
   cp .env.example .env
   ```
5. Run the local backend development server:
   ```bash
   python -m uvicorn backend.main:app --reload --port 8000
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 3. Running Unit Tests

Before submitting any code changes, ensure all unit tests pass to guarantee pipeline stability.

```bash
# Run backend test suite
.venv/bin/python -m unittest backend/tests/test_pipeline.py
```

---

## 4. Submitting a Pull Request (PR)

1. **Fork the Repository**: Create a personal copy of the repository on GitHub.
2. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/your-awesome-feature
   ```
3. **Write Clear, Clean Code**:
   - Follow Python PEP 8 style guidelines.
   - Follow React/TypeScript conventions for frontend code.
   - Do **NOT** commit any private API keys, credential JSON files, or production `.env` files.
4. **Commit Your Changes**: Use descriptive and concise commit messages:
   ```bash
   git commit -m "feat(matching): add turnover-based filter to matching heuristics"
   ```
5. **Push to Your Fork**:
   ```bash
   git push origin feature/your-awesome-feature
   ```
6. **Open a Pull Request**: Submit the PR against our `master` branch on GitHub. Please describe the changes, how you tested them, and any related issues.

---

## 5. Security & Bug Reports

If you discover a security vulnerability or critical bug, please do **NOT** open a public issue. Instead, review our [SECURITY.md](file:///Users/nayan/Documents/Sprint%2030%20days/Open%20AI%20Intelligence/opportunity-ai-engine/SECURITY.md) to report it responsibly.
