# Grupus

> A lightweight, flexible collaboration platform that blends real-time chat with structured teamwork — without the bloat.

---

## 🚀 Overview

**Grupus** is a modern collaboration system designed for people who want to work together naturally.

It combines:

* the **simplicity and speed** of chat apps like WhatsApp or Discord,
* the **organization** of tools like Trello or Classroom,
* without becoming rigid, corporate, or over-engineered.

Grupus is not limited to businesses or universities. It works just as well for:

* students
* hackathon teams
* community groups
* startups
* clubs
* families or informal teams

If people need to **talk, organize, and get things done together**, Grupus fits.

---

## 🧠 Core Concept

Grupus is a **multi-tenant, user-driven platform**.

* Anyone can create or join a **group** (also called a *tenant*)
* Each group acts as an **independent workspace**
* Every workspace has its own:

  * members
  * chat channels
  * tasks
  * shared resources

The system adapts to the group — not the other way around.

A class does not work like a startup.
A startup does not work like a family group.

Grupus respects that.

---

## 🔑 Key Features

### 1️⃣ Groups (Dynamic Workspaces)

* Public, private, or invite-only groups
* Each group is fully isolated from others
* Groups can represent:

  * a class
  * a project
  * a team
  * an event
  * a community

#### Dynamic Metadata

Admins can define **custom fields** per group, such as:

* project deadlines
* supervisors
* roles
* priorities
* custom labels

No hardcoded assumptions. No unnecessary constraints.

---

### 2️⃣ Real-Time Chat (The Core)

Chat is the heart of Grupus.

* Real-time messaging (Slack / Discord style)
* Channel-based or thread-based discussions
* System messages for activity tracking, e.g.:

  * *Task "Design UI" moved to In Progress*
  * *New resource uploaded: Lecture Notes*

Chat is not separate from work — it *drives* the work.

---

### 3️⃣ Task Management (Simple but Serious)

Grupus uses a **clean Kanban-style workflow**:

```
Not Started → In Progress → Done → Archived
```

Each task supports:

* assignees
* due dates
* comments
* attachments
* status updates

#### Chat ↔ Tasks Integration

* Tasks can be created directly from chat messages
* Task updates automatically reflect in chat

No Jira-level complexity. Just what’s needed.

---

### 4️⃣ Shared Resources

Each group has a shared resource space:

* notes
* images
* videos
* documents
* downloads

Resources can be:

* linked to tasks
* referenced in chat
* accessed by all authorized members

---

### 5️⃣ User Experience

Grupus is designed to feel **familiar instantly**.

* Open a group → see chat
* Switch tabs effortlessly:

  * Chat
  * Tasks
  * Resources
  * Members

No training manuals. No steep learning curve.

Built for real people — not enterprise demos.

---

## 🧩 Technical Architecture

### Backend

* **Django**

  * authentication & authorization
  * group and tenant management
  * task logic
  * permissions
  * REST APIs

#### Multi-Tenancy Strategy

* Single database
* Tenant ID on each record
* Clean separation between groups
* Easier scaling and maintenance

#### Dynamic Data Models

* PostgreSQL `JSONField`
* Flexible metadata tables
* Supports group-specific schemas without migrations

---

### Real-Time Layer

Options:

* **Django Channels**
* or **Node.js + Socket.io** (microservice)

Communication via:

* Redis pub/sub
* message queues

Chat and notifications remain fast and scalable.

---

### Database

* **PostgreSQL**
* Strong relational integrity
* Native JSON support for flexible structures

---

### Frontend

* React / Vue / Flutter Web
* Clean, tab-based interface
* Optimized for speed and clarity

---

### Authentication & Storage

* JWT or OAuth2 (with refresh tokens)
* File storage:

  * AWS S3
  * Supabase
  * CDN-backed Django storage

---

## 🎯 Design Philosophy

Grupus follows a few core principles:

* **Familiar before powerful**
* **Structure only where it helps**
* **Chat-first collaboration**
* **Modular and microservice-friendly**
* **Lightweight, not bloated**

Every feature earns its place.

---

## 🏁 Vision & Goal

Grupus aims to sit in the sweet spot:

* Easier than Jira
* More organized than WhatsApp
* More flexible than Classroom
* Lighter than Slack

It’s a collaboration platform that respects how people actually work — not how enterprise tools assume they do.

---

## 📌 Status

Grupus is under active development.

Planned phases:

* **MVP** — core groups, chat, tasks
* **v1** — resources, metadata, permissions
* **v2** — integrations, automation, analytics

---

## 🤝 Contributing

This project is open to iteration and evolution.

If you believe collaboration tools should be **human-first**, you’ll feel at home here.

---

**Grupus** — Talk less about work. Get more done.
