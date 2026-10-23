### Title
ADR-001: Use Postgresql as the Primary database

### Status
Accepted

### Context

PostgreSQL was initially selected because of prior familiarity with the technology, without a formal comparison of alternative databases. As the platform evolved, its relational modeling, transaction support, and concurrency capabilities became relevant to the system's requirements.

The API needed a database that could support complex data relationships, including Users, clients, cases, assignments, and audit logs with relationships between them. Also postgresql allow ACID operations, such as updating a case and recording its audit history, we also needed a Flask API accessed by potentially concurrent users, and finally we have a self-hosted server that needs a persistent database. 

### Decision

PostgreSQL is the primary relational database for the application's development and deployed environments. SQLite is retained for isolated automated testing.

### Consequences

#### Positive: 

 -Strong transactional guarantees (ACID)
 -The relational model
 -Great tooling ecosystem, extensive documentation tools, and community support.

#### Negative: 

 -Operational responsibility, since we need to manage PostgreSQL ourselves on Ubuntu Server, 
 -Backups and recovery	We must implement and verify database backups and restoration
 -Resource consumption	PostgreSQL requires server resources and configuration
 -Connection management	We need to consider connection pools and limits as concurrency increases
 -Testing differences	SQLite tests may not reproduce every PostgreSQL-specific behavior