# Academic Project Report: Database Management System for Renewable Energy Client Relationship Management (LivoCRM)

## 1. Introduction

### 1.1 Problem Statement
In the rapidly growing renewable energy sector, Managing complex Business-to-Business (B2B) client relationships, multi-stage solar installation deals, and continuous sales activities requires a robust, scalable, and intelligent system. Traditional spreadsheet-based methods of managing energy clients lead to scattered data, missed follow-ups, and an inability to accurately forecast revenue based on deal pipeline progression. Furthermore, sales representatives often struggle with manual data entry, which detracts from their core task of building client relationships and closing energy infrastructure deals. This creates an urgent necessity for an integrated Database Management System (DBMS) capable of tracking clients, evaluating lead opportunities, charting pipeline stages, and utilizing AI-driven analytics to optimize the sales process.

### 1.2 Domain Explanation (Energy)
This project focuses on the **Energy** domain, specifically tailored as an Energy Client Relationship Management (CRM) system for organizations providing solar panels, wind turbine installations, and energy efficiency consulting to commercial clients. In this domain, a "Deal" represents a potential contract to install renewable energy infrastructure. A "Contact" represents a facility manager or corporate decision-maker. The pipeline stages define the lifecycle of energy infrastructure sales—from initial lead qualification, site assessment (proposal), contract negotiation, to closed-won execution. 

### 1.3 Objectives of the System
The primary objectives of the LivoCRM Database Management System include:
1. **Centralized Data Repository:** To provide a single source of truth for all B2B contacts, activities, and commercial energy deals.
2. **Pipeline and Sales Tracking:** To implement a structured deal lifecycle that allows energy sales representatives to move prospective contracts through configurable pipeline stages.
3. **Data Integrity and Consistency:** To utilize relational database constraints, foreign keys, and Normalization principles to prevent data anomalies and orphaned records.
4. **AI-Assisted Operations:** To integrate intelligent chat models that can autonomously add leads, track activities, and summarize the health of the energy deal pipeline.
5. **Real-time Analytics:** To leverage complex SQL aggregations to calculate win rates, weighted revenue forecasts, and summary KPIs instantly.

### 1.4 Real-World Relevance
In enterprise energy project development, sales cycles span months and involve millions of dollars. Misplacing a note or incorrectly anticipating the probability of a deal closure can significantly impact quarterly revenues and resource planning. By applying advanced DBMS principles, this system ensures high availability, atomicity of transactions, data reliability, and offers AI-driven insights that directly augment commercial efficiency.

---

## 2. Entity-Relationship (ER) Design

The ER design translates the business logic of our Energy CRM into a structured blueprint. The model defines the fundamental entities participating in the system and maps out how they interact.

### 2.1 Entities and Attributes

1. **User:** Represents the energy sales representatives and administrators.
   - *Attributes:* `id` (Primary Key), `email`, `hashed_password`, `full_name`, `plan`, `created_at`, `updated_at`.
2. **Contact:** Represents a client, such as a localized facility manager or a multinational corporation's procurement officer.
   - *Attributes:* `id` (Primary Key), `user_id` (Foreign Key), `name`, `email`, `phone`, `company`, `tags`, `lead_score`, `notes`, `source`, `ai_session_id`, `created_at`, `updated_at`.
3. **Deal:** Represents a prospective energy project or contract.
   - *Attributes:* `id` (Primary Key), `user_id` (Foreign Key), `contact_id` (Foreign Key), `title`, `value` (monetary magnitude of the installation), `stage`, `status`, `expected_close`, `notes`, `source`, `ai_session_id`, `created_at`, `updated_at`.
4. **PipelineStage:** Defines the sequence of steps an energy deal goes through.
   - *Attributes:* `id` (Primary Key), `user_id` (Foreign Key), `name`, `position`, `created_at`.
5. **Activity:** Represents interactions (meetings, site assessments, calls) associated with a contact or deal.
   - *Attributes:* `id` (Primary Key), `user_id` (Foreign Key), `contact_id` (Foreign Key), `deal_id` (Foreign Key), `type`, `description`, `occurred_at`, `created_at`.
6. **ChatSession & ChatMessage:** Represents AI interactions logging autonomous data generation.
   - *Attributes (Session):* `id` (Primary Key), `user_id` (Foreign Key), `title`, `status`, `created_at`, `updated_at`.
   - *Attributes (Message):* `id` (Primary Key), `session_id` (Foreign Key), `role`, `content`, `intent`, `created_at`.

### 2.2 Relationships

- **User to Contact (1:N):** One sales rep manages multiple contacts. 
- **User to Deal (1:N):** One user oversees multiple energy contracts.
- **Contact to Deal (1:N):** One corporate client can have multiple separate solar installations/deals over time.
- **Deal to Activity (1:N):** Multiple site assessments and meetings can happen for one deal.
- **Contact to Activity (1:N):** Various emails and phone calls are logged under a specific contact.
- **User to ChatSession (1:N):** A user can initiate multiple AI chat threads.
- **ChatSession to ChatMessage (1:N):** A session contains a sequence of messages.

### 2.3 ER Diagram

```mermaid
erDiagram
    USER ||--o{ CONTACT : manages
    USER ||--o{ DEAL : owns
    USER ||--o{ PIPELINE_STAGE : configures
    USER ||--o{ ACTIVITY : performs
    USER ||--o{ CHAT_SESSION : initiates

    CONTACT ||--o{ DEAL : has
    CONTACT ||--o{ ACTIVITY : involves
    
    DEAL ||--o{ ACTIVITY : logs

    CHAT_SESSION ||--o{ CHAT_MESSAGE : contains
    CHAT_SESSION ||--o{ CONTACT : generates
    CHAT_SESSION ||--o{ DEAL : generates

    USER {
        uuid id PK
        string email
        string full_name
        string plan
    }
    CONTACT {
        uuid id PK
        uuid user_id FK
        uuid ai_session_id FK
        string name
        string company
        int lead_score
    }
    DEAL {
        uuid id PK
        uuid user_id FK
        uuid contact_id FK
        uuid ai_session_id FK
        string title
        float value
        string stage
        date expected_close
    }
    ACTIVITY {
        uuid id PK
        uuid user_id FK
        uuid contact_id FK
        uuid deal_id FK
        string type
        string description
        datetime occurred_at
    }
    PIPELINE_STAGE {
        uuid id PK
        uuid user_id FK
        string name
        int position
    }
    CHAT_SESSION {
        uuid id PK
        uuid user_id FK
        string title
        string status
    }
    CHAT_MESSAGE {
        uuid id PK
        uuid session_id FK
        string role
        string content
    }
```

---

## 3. Database Schema 

The physical schema is designed for PostgreSQL, utilizing robust data definition language (DDL) features such as UUID enhancements and comprehensive foreign key constraints cascaded effectively to prevent orphaned tuples.

### 3.1 Table: users
Stores application users (energy firm sales staff).
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name VARCHAR(255) NOT NULL DEFAULT '',
    plan VARCHAR(20) NOT NULL DEFAULT 'free',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);
CREATE INDEX idx_users_email ON users(email);
```

### 3.2 Table: contacts
Stores procurement managers and energy facility clients.
```sql
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL DEFAULT '',
    phone VARCHAR(50) NOT NULL DEFAULT '',
    company VARCHAR(255) NOT NULL DEFAULT '',
    tags JSON NOT NULL DEFAULT '[]',
    lead_score INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '',
    source VARCHAR(30) NOT NULL DEFAULT 'manual',
    ai_session_id UUID NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_ai_sess FOREIGN KEY (ai_session_id) REFERENCES chat_sessions(id) ON DELETE SET NULL
);
CREATE INDEX idx_contacts_user_id ON contacts(user_id);
```

### 3.3 Table: deals
Represents pending or completed renewable energy contracts.
```sql
CREATE TABLE deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    contact_id UUID NULL,
    title VARCHAR(255) NOT NULL,
    value NUMERIC(12, 2) NOT NULL DEFAULT 0,
    stage VARCHAR(30) NOT NULL DEFAULT 'lead',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    expected_close DATE NULL,
    notes TEXT NOT NULL DEFAULT '',
    source VARCHAR(30) NOT NULL DEFAULT 'manual',
    ai_session_id UUID NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT fk_deal_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_deal_contact FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
    CONSTRAINT fk_deal_ai FOREIGN KEY (ai_session_id) REFERENCES chat_sessions(id) ON DELETE SET NULL
);
```

### 3.4 Table: activities
Logs chronological interactions (e.g., site appraisals, quote emails).
```sql
CREATE TABLE activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    contact_id UUID NULL,
    deal_id UUID NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'note',
    description TEXT NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT fk_act_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_act_contact FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
    CONSTRAINT fk_act_deal FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE SET NULL
);
```

### 3.5 Table: pipeline_stages
Maps the specific pipeline layout required for the sales workflow.
```sql
CREATE TABLE pipeline_stages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT fk_pipe_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

---

## 4. Normalization

Normalization is an essential design technique to decrease data redundancy, ensure high integrity, and eliminate Insert, Update, and Delete anomalies. Our schema rigorously applies these principles.

### 4.1 First Normal Form (1NF)
**Rule:** Each table cell should contain a single, atomic value. No repeating groups.
- *Before 1NF application:* A user might store multiple tags as comma-separated strings inside a text field. Activities for a deal might just be a bloated appending text block in the `deals.notes` column.
- *After 1NF application:* The `activities` are split into a completely separate table where each individual interaction (meeting, call) is its own row with an atomic `occurred_at` timestamp.
- *Exception noting:* The `tags` array on the `contacts` table utilizes a PostgreSQL native `JSON`/`JSONB` array type. While historically this breaches strict relational atomic 1NF logic, modern RDBMS standardizes JSON structures as atomic data types that can be natively queried at high speed via index architectures like GIN/GiST.

### 4.2 Second Normal Form (2NF)
**Rule:** Must be in 1NF. All non-key attributes must rely completely on the entire primary key (no partial dependency). 
- Since all our tables utilize a surrogate universally unique identifier (UUID) as a single column Primary Key (`id`), all attributes invariably depend entirely on that singular PK. By definition, any relation with a single-attribute primary key that is in 1NF is inherently in 2NF.

### 4.3 Third Normal Form (3NF)
**Rule:** Must be in 2NF. All non-key attributes should not depend on any other non-key attributes (no transitive dependency).
- *Scenario Evaluation:* If the `deals` table contained `contact_name` and `contact_company` directly inside it, it would violate 3NF because `contact_company` would transitively depend on `contact_id`, not the `deal_id`.
- *Correction in our Schema:* The system stores only `contact_id` as a foreign key within the `deals` table. If the application needs to know the company of the contact associated with a Solar Installation Deal, it performs a relational `JOIN` on the `contacts` table instead of storing duplicated proxy data.

### 4.4 Avoidance of Anomalies Summary
- **Update Anomaly:** If a Corporate Energy Client changes their company name, we only update it once in the `contacts` table. All associated dozens of past deals inherently refer back correctly.
- **Delete Anomaly:** Using `ON DELETE CASCADE` and `ON DELETE SET NULL`. If a User account is purged, their isolated pipeline stages and deals automatically cascade to deletion, preventing orphaned garbage data. If a contact is deleted, the deals are retained but the `contact_id` is smartly `SET NULL`.

---

## 5. Modules of the Application

The system adopts a modular architectural pattern aligning with Domain-Driven Design concepts.

### 5.1 Auth and User Module
This module is responsible for authenticating sales representatives securely utilizing JWT (JSON Web Tokens) and bcrypt password hashing. It issues access tokens that encapsulate the user context required by all other endpoints. It handles registration, login validation, and profile management for the energy traders/reps.

### 5.2 Contact Management Module
Allows for comprehensive CRUD (Create, Read, Update, Delete) operations on client networks. Contains sophisticated filtering methods. Includes the tracking of the `lead_score`, which is calculated via Machine Learning algorithms judging the likelihood of the client converting to a lucrative contract.

### 5.3 Deal and Pipeline Module
The epicenter of the Energy CRM. Handles the financial prospects of the firm. It tracks the magnitude (`value`) of the power installation and its progression across the workflow (Lead → Qualified → Site Appraisal → Negotiation → Closed). Includes endpoints that modify state variables and execute timeline recalculations.

### 5.4 AI Agent & Chat Module
An advanced module designed to act as an asynchronous assistant for the sales rep. Built on top of `ChatSession`, `ChatMessage`, and `ChatAction` tables. The salesperson can text "I just met with John Doe from SolarTech, add him as a lead", and the LLM module digests the context, interfaces with the Database, creates the contact, links the session using the `ai_session_id`, and replies affirmatively.

### 5.5 Analytics & Forecasting Module
Executes heavy SQL aggregations to calculate core business metrics. Outputs total pipeline value, computes win rates grouping by stages, and provides a probabilistically weighted forecast (a \$1,000,000 wind farm deal in "Qualified" stage might weigh 25%, outputting $250,000 expected forecast).

---

## 6. Database Connectivity (SQLAlchemy Async ORM)

While standard Java applications use JDBC for database connections, this modern Python ecosystem leverages **SQLAlchemy**, a powerful SQL toolkit and Object-Relational Mapper (ORM), via the high-performance asynchronous `asyncpg` driver.

### 6.1 Connection Flow Execution
1. **Engine Instantiation:** The application reads the `.env` target and calls `create_async_engine(DATABASE_URL)`. This compiles the connection pool rules and loads the Postgres async driver.
2. **Session Factory Preparation:** `async_sessionmaker` builds a context factory that governs atomic transactions. Setting `expire_on_commit=False` ensures objects remain resident in application memory after a transaction is closed.
3. **Dependency Injection:** At runtime, the FastAPI web framework invokes the `get_db` generator dependency. This executes `async with async_session() as session: yield session`. 
4. **Execution:** The router executes statements, yielding control back to the event loop, effectively preventing threads from blocking while waiting for network I/O to the DBMS engine.

### 6.2 Connection String Profile
Format: `postgresql+asyncpg://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}`
Example: `postgresql+asyncpg://postgres:securepass!@localhost:5432/livo_crm`

Sample connection module (`database.py`):
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Initializes the high-performance async driver connected to PostgreSQL
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

# Factory ensuring database session bounds and lifecycle management
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    """Shared declarative base mapping Python Classes exactly to SQL Tables."""
    pass
```

---

## 7. Screenshots and Output Simulation

As this is a backend-heavy data system description, the interactive outputs are logically simulated via expected front-end rendering scenarios and JSON APIs.

### 7.1 Dashboard Overview (Analytics Mock)
**UI Layout Description:**
- Top row consists of 4 large metric cards: _"Total Contacts: 1,420"_, _"Active Deals: 45"_, _"Pipeline Value: $14.5M"_, _"Expected Forecast: $4.2M"_.
- A large categorical bar chart showing "Win/Loss Funnel" plotting `Closed Won` vs `Negotiation` stages.
- A feed on the right mapping `Recent Activities`.

**Simulated Application API JSON Fetch:**
```json
{
  "contacts": 1420,
  "deals": 45,
  "activities": 312,
  "pipeline_value": 14500000.0,
  "won_value": 8500000.0
}
```

### 7.2 Deal Pipeline Kanban Board
**UI Layout Description:**
- A wide Kanban board divided into vertical columns representing `PipelineStage` entities (e.g., *Lead*, *Proposal*, *Negotiation*).
- Interactive drag-and-drop cards mapping to the `deals` table.
- Card details simulate showing: 
  > **Project Alpha Solar Array**
  > Contact: Sarah Jenkins (NextGen Energies)
  > Value: $650,000 | Close: Oct 20th 

### 7.3 AI CRM Chat Console 
**UI Layout Description:**
- Right-sided floating modal with chat bubbles.
- **User:** "Prepare a summary of all my solar deals currently in negotiation."
- **Assistant:** "You have 3 deals in negotiation spanning $2.1M. One with EcoCorps and two with GridVital." -> The system autonomously fires `SELECT` SQL statements behind the scenes to fetch this.

---

## 8. Sample Code 

The following extracts represent heavily integrated components of the MVC application, detailing asynchronous data querying, ORM implementations, AI Machine Learning models, and business logic routing.

### 8.1 API Entry Point and Router Management (`main.py`)
This section maps the API endpoints to the web server space, defining the overarching CRM interface footprint.

```python
"""LivoCRM — FastAPI entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import (
    auth_router, contacts_router, deals_router,
    activities_router, analytics_router, ai_router,
    chat_router, ws_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bind models directly to SQLAlchemy Declarative Meta prior to server start
    import app.models  # noqa: F401
    yield

app = FastAPI(
    title="LivoCRM Energy API Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# Standard Security and CORS integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api"
app.include_router(analytics_router, prefix=API)
app.include_router(contacts_router, prefix=API)
app.include_router(deals_router, prefix=API)
app.include_router(ws_router)  # Handles Live WebSocket push alerts
```

### 8.2 Database ORM Models Implementation 

The pythonic representation of the Entity-Relationship structures using typed mappings.

```python
"""Contact Model definition linked to the users table."""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    company: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    
    # Store dynamic tag arrays using Postgres highly efficient JSON columns
    tags: Mapped[list] = mapped_column(JSON, nullable=False, server_default="[]")
    lead_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    
    # AI provenance tracking foreign keys
    ai_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    
    # Bi-directional relational bindings mapped directly via the ORM engine
    user = relationship("User", back_populates="contacts")
    deals = relationship("Deal", back_populates="contact")
    activities = relationship("Activity", back_populates="contact")
```

### 8.3 Advanced SQL Analytical Aggregation (`routers/analytics.py`)
This file highlights deep SQL queries running via the asynchronously engineered session. Notice the use of `func.sum` and `group_by`.

```python
"""Analytics router — KPI summaries, win-rate funnel, revenue forecast."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.models.deal import Deal
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/forecast")
async def forecast(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Weighted revenue forecast calculation.
    Multiplies literal projected Deal cash values against probability constants
    based on the deal's current relational pipeline stage mapping.
    """
    stage_weights = {
        "lead": 0.1,
        "qualified": 0.25,
        "proposal": 0.5,
        "negotiation": 0.75,
        "closed_won": 1.0,
        "closed_lost": 0.0,
    }
    
    # Build and execute the SELECT (stage, sum(value)) FROM deals WHERE ... GROUP BY stage SQL
    result = await db.execute(
        select(Deal.stage, func.sum(Deal.value))
        .where(Deal.user_id == user.id, Deal.status == "active")
        .group_by(Deal.stage)
    )
    
    breakdown = {}
    weighted_total = 0.0
    
    for stage, total in result.all():
        weight = stage_weights.get(stage, 0.1)
        weighted = float(total) * weight
        breakdown[stage] = {
            "raw": float(total), 
            "weight": weight, 
            "weighted": round(weighted, 2)
        }
        weighted_total += weighted

    return {"forecast": round(weighted_total, 2), "breakdown": breakdown}
```

### 8.4 Support Code: Machine Learning Data Synthesizer (`ml/generate_data.py`)
Showcases the programmatic heuristic mechanism to generate synthetic data for the ML classification network that operates adjacent to the database logic to assign `lead_score`.

```python
"""Generate synthetic CRM data for training the lead-scoring model."""
import random
import pandas as pd

random.seed(42)
ROWS = 2000

def generate():
    records = []
    for _ in range(ROWS):
        has_company = random.choice([0, 1])
        has_phone = random.choice([0, 1])
        tag_count = random.randint(0, 5)
        notes_length = random.randint(0, 500)
        activity_count = random.randint(0, 20)
        days_since_last_activity = random.randint(0, 90)

        # Basic weighted polynomial equation determining the heat map intensity of the lead
        score = (
            has_company * 15
            + has_phone * 10
            + tag_count * 5
            + min(notes_length / 50, 10)
            + activity_count * 3
            - days_since_last_activity * 0.5
        )
        
        if score > 40:
            label = "hot"
        elif score > 20:
            label = "warm"
        else:
            label = "cold"

        records.append({
            "has_company": has_company,
            "has_phone": has_phone,
            "tag_count": tag_count,
            "activity_count": activity_count,
            "days_since_last_activity": days_since_last_activity,
            "label": label,
        })

    df = pd.DataFrame(records)
    df.to_csv("ml/training_data.csv", index=False)
    print(f"✓ Generated {ROWS} records for Machine Learning Model Training")

if __name__ == "__main__":
    generate()
```

---

## 9. Conclusion

### 9.1 Summary of the System
The LivoCRM platform showcases an exquisitely crafted Database Management System fundamentally engineered to sustain demanding operational pipelines inherent in the B2B renewable energy commercial marketplace. By enforcing uncompromising relational data integrity standards spanning a multitude of normalized tables (`users`, `contacts`, `deals`, `activities`), the system eradicates destructive redundancies and transactional anomalies.

### 9.2 Key Achievements
- **Analytical Powerhouse:** Demonstrated the immense flexibility of aggregated SQL, translating raw data into mathematically nuanced weighted enterprise forecast matrices.
- **Architectural Soundness:** Effectively maintained standard Normal Forms (1NF through 3NF) using native RDBMS tools and foreign keys operating gracefully via `ON DELETE CASCADE` cascading actions.
- **Modern Paradigms deployed:** The integration of decoupled Machine Learning systems parsing raw database rows into inferenced predictive behaviors ("Hot" or "Cold" leads), coupled with bleeding-edge async execution, represents the zenith of contemporary DBMS deployment strategies.

### 9.3 Future Improvements
1. **Schema Sharding / Partitioning:** As the application gathers immense rows over years of operation, implementing table partitioning based on the `created_at` timestamp parameter per respective financial quarter will optimize query search windows dramatically.
2. **Read-Replicas Construction:** Offloading the intensive `analytics_router` aggregation queries exclusively to a secondary DBMS Read-Replica structure will severely free up the Primary Node to dedicate all compute latency explicitly towards writing new deals and executing `INSERT`/`UPDATE` mutation operations.
3. **Graphing Extensions:** Integrating Graph Database sub-networks (like Neo4j alongside PostgreSQL) to map out extremely granular interpersonal relationships inside massive multinational corporate entities (who reports to whom inside a contact organization).
