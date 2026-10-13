# System Architecture — Client Intake Platform

## 1. Purpose and Scope

This document describes the current deployed architecture of the Client Intake Platform, including the React frontend, public access path, reverse proxy, application server, Flask API and PostgreSQL database.

This is a platform to keep track of clients, cases/projects, where users can update the information, review and work with those, also the platform keep track of everything that the users does and when it happened. The platform include a login and authenticated session handling feature for security and authorization based feature as well. The idea is that the users can understand and update everything while the data is safe.

## 2. Functional Requirements

Authenticate active users
Manage users according to admin/staff authorization
Create and update clients
Create and manage cases
Assign users to cases
Move cases through controlled workflow transitions
Soft-delete cases according to authorization rules
Record important case changes in audit logs
Retrieve filtered/paginated case data

## 3. Non-Functional Requirements

Security of the data.
Reliability of the platform
API latency and database-query performance should be measurable before performance targets are defined.
Maintainability — the codebase should remain modular, testable and understandable as features are added.
Auditability and data protection suitable for sensitive client workflows.

## 4. Current Architecture

![Alt text](https://res.cloudinary.com/smivyk2c/image/upload/v1791845537/API_architecture.png)

## 5. Component Responsibilities

### React / Vite Frontend

The frontend of the app, used for the UI/UX, the use of React is important to handle the different stages and the reuse of several components, also allow to send the required information to the backend via API, receives the response, update the state and display the information for the user.

### Public Access Layer / Cloudflare Tunnel

The cloudflared is the current solution to allow the local server to expose the API to the internet and to connect with the frontend. 

### Nginx

Nginx
- receives HTTP requests
- acts as reverse proxy
- forwards requests to Gunicorn on 127.0.0.1:8000
- prevents Gunicorn from being directly exposed
- forwards request headers/context.

### Gunicorn 

Gunicorn manages Python worker processes and invokes the Flask application through the WSGI interface.

### Flask API

The engine of the API with routing, authentication hooks, authorization enforcement, input validation, business logic through services,
SQLAlchemy interaction, serialization/error responses and connections with the database through SQLAlchemy.

### PostgreSQL

The database holding the information about the users, clients, cases and the logs.

## 6. Request Lifecycle

Example scenario:
"Authenticated user requests GET /cases"

In the browser the authenticated user will click the cases link, the frontend with React will route the user to the cases page, first obtain the JWT token from the local storage of the browser, with this token will make a HTTP request to the API through the cloudflared tunnel, then the nginx reverse proxy will receive the HTTP request, forward the request to the gunicorn server, which will invoke the flask endpoint, then with the GET method and the token will verify that the user is actually authorized for use this resource, then will call the  get_cases() services, this services will query the database using the ORM SQLalchemy to look for all the cases, after that, if everything is ok, the response will travel back as Flask Json response, through gunicorn, nginx and the cloudflared tunnel to react, finally react will display in table.

## 7. Authentication and Authorization Flow

After the login, the front sent the user email and the user password as a HTTP post request, then the route send that information to the login service that checks this information, verifies the submitted password against the stored bcrypt password hash. If both are correct the service creates the token sends it to the frontend as a response. 

After that the token is store in the localstorage of the browser, and send with every request from the front to the backend.

Every protected route checks for the token and with this the identity of every user through the user ID.

## 8. Data and Persistence

PostgreSQL
→ server-side persistent business data

localStorage
→ client-side persistent authentication token

React component state
→ ephemeral client state

Flask/Gunicorn memory
→ ephemeral application-process state

## 9. Trust Boundaries

| Boundary           | What crosses it         | Why it is untrusted / protected               | Controls |
|--------------------|-------------------------|-----------------------------------------------|----------|------------------------------------|
| Browser → API      | JWT, JSON, IDs, filters | Client controls requests                      | JWT validation, authorization, input validation |
| Internet → server  | HTTP traffic            | Public network | Cloudflare, Nginx, Firewall ufw |
| Nginx → Gunicorn   | Proxied HTTP            | Internal server communication                 | Gunicorn bound to `127.0.0.1:8000` |
| Flask → PostgreSQL | Queries/data            | Persistent data boundary                      | SQLAlchemy, DB credentials |

## 10. Failure Modes

| Failure | What the user experiences | What may still be healthy | Diagnosis / recovery |
|-----------------------------------|----------------------------------|-------------------------------------------|---------------------------|
| **Cloudflare Tunnel unavailable** | Public frontend cannot reach API | Nginx, Gunicorn, Flask and PostgreSQL still work locally/LAN | Check `cloudflared`; restart tunnel |
| **Nginx fails** | Requests through Nginx fail | Gunicorn may still answer on `127.0.0.1:8000` | `systemctl status nginx`, `nginx -t`, logs |
| **Gunicorn worker crashes** | One request may fail; remaining worker may continue | Nginx, PostgreSQL, another Gunicorn worker | Check systemd/Gunicorn logs; worker/master can restart |
| **PostgreSQL unavailable** | DB-backed endpoints fail | Nginx/Gunicorn/Flask process can remain running | Check PostgreSQL service/logs/connection; restore DB availability |
| **Physical server fails** | Entire backend unavailable | Nothing on that host | Single-server architecture means total outage; restore host/backups |

## 11. Current Scaling Model

One physical server
One Nginx instance
One Gunicorn service
Two Gunicorn workers
One Flask application
One PostgreSQL instance
No Redis
No distributed cache
No load testing yet
No measured latency/throughput baseline yet

Scaling question to answer in the near future: 

At what level of concurrent traffic do API latency and error rates begin to degrade?
Which component becomes the first bottleneck under load: Gunicorn workers, PostgreSQL, server CPU/RAM, or the network/tunnel?
How does database connection usage behave as concurrent requests increase, and when would connection-pool limits need to be adjusted?
What becomes the bottleneck as concurrent requests increase?
How would multiple Flask instances share rate-limit/revocation/cache state?
How many database connections can the application safely open before PostgreSQL becomes constrained?

We cannot currently say which bottleneck appears first because load testing and endpoint/database instrumentation have not yet been implemented.

## 12. Current Limitations

No endpoint latency metrics
No database query metrics
No load/concurrency baseline
No rate limiting
No Redis/shared ephemeral state
No JWT revocation/blocklist
Temporary public tunnel
Single server = single point of failure
No automated backup/restore validation yet
No stable production hostname
No containerized deployment yet


## 13. Future Evolution


### Product Evolution
Charts
Reports

### Architecture / Infrastructure Evolution
Redis
Docker
Observability
Object storage
Multiple application instances
Kubernetes experiment

## 14 Interview Summary

what the system does?
The Client Intake Platform is a case-operations platform that looks to facilitate the tracking of the clients, and the work that is being completed for cases or projects, the idea is to make it simpler enough for the user to find and use all the features, but also but the managers to understand what is going on with their business. The catch is that this platform is customizable, secure and useful to make sure the work in being done correctly and no information is lost. 

how a request travels?

For this system the request travel from the browser, using the frontend that built using React, the client make the request and the frontend send that request using a JSON through first the cloudflared tunnel, then gets to the reverse proxy nginx that get that request and passed to the gunicorn worker, that then passed to the endpoint, the endpoint will validate the identity of the user, by using the JWT token, after passing the validation, will use a specific service to query the database using SQLalchemy, then the service will return the response using a JSON and will travel back through the guinicorn, the nginx proxy, the cloudflared tunnel to the frontend, that will received and display it in the browser.. 

where security/business logic/data persistence live

The business logic live in the Flask services, the requests and the authorization are handle by Flask through the endpoints, the data models are handle by SQLAlchemy. For the users, clients and cases/projects data these live in the Postgresql data base. 

what the current limitations are

The current limitations, include security issues with the logout and the persistency of the Token after that, the API is not containerized and this limits the options to use some external server for now,  no observability or monitoring of the endpoints and the database that allows to see security issues but also performance issues of the API, finally no rate limiting. 


