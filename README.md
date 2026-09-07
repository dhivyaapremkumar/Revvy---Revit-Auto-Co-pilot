# REVVY — AI Copilot for Autodesk Revit

> **Natural Language → AI Reasoning → Structured Tools → Revit Actions**

REVVY is an experimental **AI-powered copilot for Autodesk Revit and BIM workflows**, designed to explore how Generative AI can move beyond answering questions and interact with professional design software through controlled tools.

The goal is simple:

**Reduce repetitive BIM operations and allow users to interact with Revit using natural language.**

---

## 🚀 What REVVY Does

Instead of manually navigating multiple Revit commands, a user can provide instructions such as:

> “Create a bedroom next to the living room.”

REVVY interprets the request, converts it into structured parameters, selects the appropriate Revit tool, and executes the supported operation.

The project explores a **Read → Reason → Act → Validate** approach to AI-assisted BIM automation.

---

## 🧠 Architecture

```text
USER
  │
  ▼
REVVY UI
React + TypeScript
  │
  ▼
FastAPI Backend
  │
  ├── Authentication & Sessions
  ├── AI / LLM Orchestration
  ├── RAG / Domain Knowledge
  └── Structured Tool Selection
          │
          ▼
     Revit Tool Layer
          │
          ▼
     Autodesk Revit
          │
          ▼
   Model Result / Feedback
```

The core design principle is to separate **AI reasoning from deterministic execution**.

The LLM understands user intent and determines the required operation, while structured tools/APIs perform the actual BIM actions.

---

## 🛠 Key Capabilities

### Model Intelligence

REVVY can work with structured tools for retrieving information such as:

* Levels
* Wall types
* Walls
* Rooms
* Plot boundaries
* Element information

### Revit Automation

Supported/experimental workflows include:

* Create walls
* Create rooms
* Create doors
* Create windows
* Create property/plot boundaries
* Generate floor-plan elements
* Move elements
* Modify walls
* Delete elements

### Building Compliance

REVVY also explores AI-assisted regulatory checking using **RAG over Tamil Nadu building regulations**.

The architecture combines:

**RAG for knowledge retrieval + deterministic logic for calculations + AI for interpretation.**

Example:

```text
User Question
      ↓
Retrieve Relevant Regulation
      ↓
Extract Context
      ↓
Apply Structured Calculation / Rule
      ↓
Return Result + Explanation
```

This approach reduces dependence on free-form LLM answers for calculations and compliance decisions.

---

## 🤖 Why Not Just Use an LLM?

REVVY is designed around the idea that an LLM should **not directly control critical model operations**.

Instead:

```text
Natural Language
      ↓
LLM Intent Understanding
      ↓
Structured Parameters
      ↓
Tool Selection
      ↓
Deterministic Revit Operation
      ↓
Validation / Feedback
```

This makes the workflow more predictable, testable and extensible.

---

## 🎙 Voice Interaction

The project also includes experimentation with a **voice-agent layer**, exploring hands-free interaction with BIM workflows.

The long-term idea is to enable interactions such as:

> “Revvy, show me the rooms on this level.”

or

> “Create a window on this wall.”

and translate them into controlled Revit operations.

---

## 💻 Technology Stack

**AI / GenAI**

* OpenAI LLMs
* RAG
* Prompt Engineering
* Structured Tool Calling
* Agentic AI concepts

**Backend**

* Python
* FastAPI
* PostgreSQL
* SQLAlchemy
* REST APIs

**Frontend**

* React
* TypeScript
* Vite

**BIM Integration**

* Autodesk Revit
* Revit Add-in / Tool Layer
* pyRevit-based experimentation

**Infrastructure**

* Docker
* GitHub Actions

---

## 📁 Project Structure

```text
Revvy---Revit-Auto-Co-pilot/
│
├── backend/
│   └── API, AI orchestration, RAG and application logic
│
├── frontend/
│   └── React/TypeScript user interface
│
├── revit-addin/
│   └── REVVY Revit integration
│
├── voice-agent/
│   └── Voice interaction experiments
│
├── agents/
│   └── Agent definitions and workflows
│
├── skills/
│   └── Supporting AI/development skills
│
├── PRPs/
│   └── Product and implementation specifications
│
└── docker-compose.yml
```

---

## 🔄 Example Workflow

```text
User:
"Create a room next to the living room."

        ↓

REVVY interprets intent

        ↓

Extracts structured parameters

        ↓

Checks available Revit context/tools

        ↓

Calls appropriate Revit operation

        ↓

Revit model is updated

        ↓

Result returned to user
```

This demonstrates how an LLM can function as an **orchestration and reasoning layer** rather than simply as a chatbot.

---

## 🎯 Problem REVVY Is Exploring

BIM professionals spend significant time navigating software interfaces and performing repetitive modelling operations.

REVVY explores whether Generative AI can create a more intuitive interaction layer between:

**Human Intent ↔ AI ↔ Domain Knowledge ↔ BIM Tools**

The broader goal is to investigate how **Agentic AI can safely interact with complex professional software**.

---

## 👩‍💻 My Role

REVVY is a hands-on GenAI project that I have developed from concept through implementation.

My work includes:

* Identifying the use case
* Designing the system architecture
* Building AI/LLM workflows
* Implementing RAG
* Designing structured Revit tools
* Connecting AI reasoning with Revit execution
* Developing frontend/backend integrations
* Testing workflows
* Debugging integration issues
* Iteratively expanding capabilities

The project combines my engineering background, business exposure and interest in building practical AI systems that solve real operational problems.

---

## 🗺 Roadmap

Future areas of exploration include:

* Stronger validation and self-correction
* Improved model awareness
* Additional Revit tools
* Structural and MEP workflows
* Multi-model/context awareness
* Drawing/plan interpretation
* OCR / vision-to-BIM workflows
* Expanded compliance automation
* Human approval for high-impact actions
* Improved voice interaction

---

## ⚠️ Project Status

REVVY is an **actively evolving experimental project**.

It is intended to demonstrate the architecture and possibilities of integrating Generative AI with BIM workflows. Some capabilities are prototypes or under active development and should not be treated as production-ready Revit automation.

---

## 👤 Author

**Dhivyaa Premkumar**

GenAI | Agentic AI | RAG | AI Automation | LLM Applications

Built as a hands-on exploration of how Generative AI can move from **conversation to real-world action**.
