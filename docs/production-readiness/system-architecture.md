# Pickup Lane — System Architecture

*Infrastructure and Technical Design Specification*

## 1. System overview

Pickup Lane is a web application built with **React and Vite** for the frontend and **FastAPI** for the backend. The backend provides an **application programming interface (API)**, allowing the website to communicate with the application's server-side services.

**Render** hosts the frontend as a Static Site, the backend as a Web Service, and the application's **PostgreSQL relational database**. Render also hosts a **background worker** for tasks that run separately from user requests and a **Cron Job** for scheduled tasks.

Pickup Lane uses several external services:

- **Firebase Authentication:** Handles user sign-in and identity.
- **Stripe:** Handles payments and refunds.
- **Cloudflare R2:** Stores venue-image files.
- **Postmark:** Delivers transactional emails, such as booking confirmations and cancellations.
- **Grafana Cloud:** Monitors application performance, errors, and service health.
- **PostHog:** Collects selected product analytics events to measure how the application is used.
- **Amazon S3 (Simple Storage Service):** Stores independent database backups for recovery.

The architecture has **three separate environments**: development, staging (a separate environment for testing before release), and production (the live application).

Production runs in Render's Ohio region with two FastAPI instances, one background worker, one Render Cron Job, and one managed PostgreSQL database. The two FastAPI instances run the same application and share the same database. Render distributes incoming API traffic between them, allowing the backend to remain available if one instance fails. However, both instances still depend on the same database and regional infrastructure.

---

## 2. Application architecture

### 2.1 Web frontend and application API

The **React/Vite frontend** is deployed as a **Render Static Site**, which hosts the website's built files. Render's **content delivery network (CDN)** serves those files from geographically distributed servers, reducing the time needed to deliver the website to users.

The browser communicates directly with the **FastAPI backend** over **HTTPS (Hypertext Transfer Protocol Secure)**, which encrypts traffic between the browser and Render. FastAPI runs as a **Render Web Service**, which executes the backend application and processes API requests rather than serving the website's static files.

### 2.2 Database and asynchronous work

**Render Managed PostgreSQL** is Pickup Lane's primary relational database, storing application records and background jobs. Production uses one managed PostgreSQL database in Render's Ohio region, without automatic database failover to a standby database.

Pickup Lane uses **asynchronous processing** to run tasks separately from incoming API requests, so users do not have to wait for those tasks to finish.

Two Render services support this arrangement:

- **Background worker:** A continuously running service that processes jobs stored in PostgreSQL, including transactional emails, payment follow-ups, retries, and reconciliation (checking external service results against Pickup Lane's records to identify and resolve discrepancies). PostgreSQL serves as the **job queue**, which stores work awaiting processing, so no separate message-queue service is needed.
- **Render Cron Job:** A service that runs tasks on a defined schedule, such as database backups and recurring maintenance. Scheduled application work that requires background processing uses the existing PostgreSQL-backed worker.

### 2.3 Authentication and application permissions

**Firebase Authentication with Identity Platform** manages user accounts and sign-in. Firebase Authentication verifies users' identities, while Identity Platform provides the managed identity service and authentication configuration supporting those sign-in operations.

**Firebase App Check** provides an additional security check to help distinguish requests from Pickup Lane's registered application from requests made by unrecognized clients. The frontend obtains an App Check token, which FastAPI verifies on API requests that require this protection. App Check helps reduce unauthorized application access but does not replace user authentication or permissions.

- **Application permissions:** FastAPI uses roles and permissions stored in PostgreSQL to control access to protected application features. Authentication through Firebase does not automatically grant those permissions.
- **Administrator authentication:** Pickup Lane administrators must use **time-based one-time password (TOTP) multifactor authentication**, requiring an additional code from an authenticator app when signing in.

### 2.4 Payments and Stripe webhooks

**Stripe** handles payments and refunds, while **PostgreSQL** stores Pickup Lane's corresponding booking and financial records.

- **Webhooks:** Webhooks are automatic HTTPS notifications sent from one service to another when an event occurs. Stripe sends payment and refund notifications to dedicated FastAPI endpoints. FastAPI verifies each webhook's **cryptographic signature**, which confirms that the notification came from Stripe and has not been altered.
- **Environment separation:** Development and staging use separate **Stripe general sandboxes** (isolated testing environments that do not process real payments). Production uses **Stripe live mode** for actual transactions. Each environment has its own API credentials and webhook-signing secrets.

### 2.5 Image storage and delivery

**Cloudflare R2** provides object storage, which stores files as individual objects within storage containers called **buckets**. R2 stores Pickup Lane's venue-image files, while **PostgreSQL** stores the references linking published images to application records.

Development, staging, and production each have two separate R2 buckets—**six buckets in total**:

- **Private storage:** A private-origin bucket for authorized administrative image uploads and processing.
- **Published storage:** A separate bucket containing processed and sanitized images (images checked and cleaned for safe publication). Production serves these images through a configured custom domain, with the `r2.dev` development endpoint disabled.

**FastAPI** coordinates authorized venue-image uploads and publication. The existing background worker handles durable image processing, cleanup, and eligible repairs through PostgreSQL-backed jobs. The existing Render Cron Job initiates scheduled image-consistency checks and hands durable follow-up work to the worker.

Each environment uses separate, access-restricted credentials for private-origin storage and image publication. These credentials are not exposed to the browser.

### 2.6 Transactional email

**Postmark Basic** handles Pickup Lane's transactional emails, including booking, cancellation, and refund notifications. **Firebase** continues to handle authentication-related emails.

Pickup Lane uses **one Postmark account with three sending servers**, one each for development, staging, and production. A Postmark sending server is a separate email-sending configuration within the account, not a physical server Pickup Lane needs to host.

- **Environment separation:** Each sending server has its own access token and webhook configuration, keeping development and staging email access separate from production.
- **Delivery reporting:** Postmark reports email delivery (acceptance by the recipient's email server), bounces (emails that could not be delivered), and suppressions (email addresses blocked from receiving further messages). Postmark sends these events to the configured FastAPI webhook endpoint for the corresponding environment.
- **Webhook authentication:** Each environment's Postmark delivery webhook uses HTTPS and its own **HTTP Basic Authentication** credentials (a configured username and password supplied with the request). These webhook credentials are separate from that environment's email-sending token. FastAPI authenticates each incoming request before processing it and deduplicates the event before updating notification records.
- **Retry limitation:** Postmark does not support API **idempotency keys**, which are unique identifiers used to prevent repeated requests from causing duplicate operations. If an email request is interrupted, Pickup Lane may not know whether Postmark accepted it, so automatically retrying could send a duplicate email.

---

## 3. Public access and security boundaries

### 3.1 Public entry points

Pickup Lane exposes two primary application HTTPS hostnames: one for the Render Static Site and one for the FastAPI backend. Published venue images use the separate Cloudflare R2 custom domain described in Section 2.5. **Domain Name System (DNS)** records direct these hostnames to their respective services. Render handles incoming HTTPS connections for the website and API without a separately deployed reverse proxy or edge-security service.

Public website requests first reach Render's global CDN, which serves the Static Site over HTTPS. Public API requests first reach Render's managed ingress; Render's load balancer terminates HTTPS and forwards requests over HTTP to the FastAPI instances. The browser calls the API directly rather than through the Static Site. FastAPI is not publicly reachable without Render's ingress, but the Web Service's default `onrender.com` address may provide another route around the canonical API hostname unless it is disabled. The final status of that address, the full ingress path, and which components may add or replace trusted forwarding information must be recorded in this document before implementation planning begins for API behavior that depends on the public request path, including liveness checks, HTTPS redirects and response headers, credentialed CORS, trusted request information, and end-to-end timeouts; client-supplied forwarding headers are not trusted by this description.

- **Cross-Origin Resource Sharing (CORS):** A browser security mechanism that determines which website origins may read responses from the API. An **origin** is the combination of protocol, hostname, and port. Because Pickup Lane's website and API use separate hostnames, FastAPI permits requests from explicitly configured website origins. For requests requiring additional checks, browsers send a **preflight request** using the HTTP `OPTIONS` method to verify permitted methods and headers. CORS does not replace authentication or application permissions.
- **Private infrastructure:** PostgreSQL, the background worker, Render Cron, and Amazon S3 backup storage are not public application endpoints. Browsers cannot connect directly to these backend services.
- **Traffic protection:** Pickup Lane requires operation-specific controls, including **rate limiting**, which restricts how frequently a caller can perform a particular operation within a defined period. Different API operation families may use different protections. Existing authentication, authorization, database constraints, and idempotency mechanisms may satisfy specific repeated-request risks when their effectiveness is verified. Request-count limits must operate across both production FastAPI instances rather than independently on each instance. The exact cross-instance request-count enforcement mechanism remains unselected; it must be resolved for the affected implementation plan once the operations and their requirements are defined. The mechanism and its request-count limits must be chosen from recorded information, such as the selected services' documented limits, the number of running API instances, measured request volume, or a recorded business decision, not from guessed values, and must be finalized and verified before production signoff. Valid CORS preflight requests, Render health checks, and authenticated Stripe and Postmark webhooks receive separate treatment so restrictions on ordinary API traffic do not interfere with those operations.
- **Outbound connections:** FastAPI, the background worker, and Render Cron communicate with external services through approved, environment-specific destinations. User-supplied addresses cannot redirect these backend connections to arbitrary destinations.

In local development, the listed backend and scheduled roles run locally when the corresponding integration is exercised.

| Backend consumer | Selected destination | Permitted operation |
| --- | --- | --- |
| FastAPI, worker, and Cron Job | The environment's Render PostgreSQL database | Application data, durable jobs, scheduled records, and backup reads, according to each component's role |
| FastAPI; worker where durable account work requires it | The environment's Firebase Authentication, Identity Platform, and App Check resources | Identity and attestation checks and approved account actions |
| FastAPI and worker | The environment's Stripe sandbox or live account | Payment and refund operations, follow-ups, and reconciliation |
| FastAPI and worker | The environment's private and published Cloudflare R2 buckets | Authorized image upload coordination, object checks, processing, publication, cleanup, and repair |
| Worker | The environment's Postmark sending server | Transactional email sends and available send-outcome checks |
| FastAPI and worker | The environment's Grafana Cloud stack | Sanitized application telemetry; FastAPI also forwards validated browser errors |
| Cron Job | The environment's Amazon S3 backup storage | Independent PostgreSQL exports |
| Authorized backend journal writer; component assignment pending | Production Oregon S3 decision journal | Protected decision writes and readback |

This inventory identifies service relationships, not approved network addresses. For each row, the consuming component, exact environment-specific endpoint, permitted operations, and redirect handling must be finalized and recorded in this document before any hosting-dependent implementation begins. Backend requests must not follow a redirect to an unapproved destination. S3's Ohio-to-Oregon replication is a storage-service operation, not another backend request. No endpoint or redirect behavior in this table is claimed to be configured or verified.

---

## 4. Environments and hosting locations

### 4.1 Environment separation

Pickup Lane separates development, staging, and production so that testing and development activities do not affect the live application. Each environment uses its own application resources, data stores, and access credentials. Sharing a provider account for billing or administration does not authorize workloads to access another environment's data.

For **Grafana Cloud**, a *stack* is a separate monitoring environment with its own logs, performance measurements, and alert settings. Pickup Lane uses three stacks so development, staging, and production monitoring data remain separate.

The environment allocations are:

| System | Development | Staging | Production |
| --- | --- | --- | --- |
| Frontend | Runs locally using Vite | Separate Render Static Site and hostname | Production Render Static Site and hostname |
| FastAPI | Runs locally | Separate Render Web Service | Render Web Service with **two instances** |
| PostgreSQL | Local database | Separate Render managed PostgreSQL database | PostgreSQL primary in Render's Ohio region |
| Background jobs and scheduling | Locally controlled execution | Separate worker and Render Cron Job | **One worker** and one Render Cron Job |
| Firebase Authentication / Identity Platform / App Check | Separate Firebase project | Separate Firebase project | Separate Firebase project |
| Stripe | Development general sandbox | Separate staging general sandbox | Live mode and production webhooks |
| Cloudflare R2 | One private and one published-image bucket | One private and one published-image bucket | One private and one published-image bucket; `r2.dev` disabled |
| Amazon S3 | Separate account with an Ohio backup-testing bucket | Separate account with Ohio and Oregon backup buckets | Separate account with Ohio backup storage and an Oregon replica |
| Postmark | Development sending server | Staging sending server | Production sending server |
| Grafana Cloud | Development monitoring stack | Staging monitoring stack | Production monitoring stack with Grafana Incident Response & Management (IRM) alert routing |
| PostHog | Separate analytics project | Separate analytics project | Separate analytics project |

**Continuous integration (CI):** Automated build and testing processes that check application changes before deployment. Pickup Lane runs CI in isolated execution environments using a temporary test database, simulated external services for unit tests, and separately restricted integration sandboxes when necessary. Ordinary CI jobs do not receive staging or production credentials.

The table states planned resource types and separation, not the identity of provisioned resources. Before any hosting-dependent implementation begins, each named system needs a safe human-readable designation for its local-development resource, automated-test and CI treatment, staging resource, and production resource, with unprovisioned assignments marked as such. The exact provider accounts, projects, services, buckets, and hostnames have not yet been designated here. Only a resource explicitly designated as production may later supply production evidence; a planned or staging resource does not qualify.

### 4.2 Regions and shared failure dependencies

The production API, background worker, Cron Job, and PostgreSQL database run in **Render's Ohio region**. Render delivers the frontend through its global CDN, rather than serving website files exclusively from Ohio.

Database backups are stored in **Amazon S3 in Ohio (`us-east-2`)** and replicated to **Oregon (`us-west-2`)**. Replication copies backup data between regions, but the Oregon copy may not be immediately up to date with the Ohio source.

Development, staging, and production use separate Amazon Web Services (AWS) accounts. These accounts are managed through **AWS Organizations**, which provides centralized account administration while retaining separate resource and permission boundaries.

Although production has two API instances, both depend on the same Ohio region, PostgreSQL primary, and Render infrastructure. A failure affecting one of these shared dependencies can therefore affect both API instances.

**Oregon is a backup location, not an active standby environment.** It does not automatically take over if production becomes unavailable. Recovering from an Ohio regional failure requires restoring the necessary data and services.

Other external services may process, store, or route data outside Ohio. Hosting the main application in Ohio therefore does not mean all Pickup Lane data remains in that region.

---

## 5. Deployment and Render runtime

### 5.1 Release arrangement

**GitHub Actions** manages Pickup Lane's release workflow from **protected branches**, which restrict how changes can be merged or deployed.

- Changes move from feature branches into **`develop`** and then to staging. Once staging testing and approval are complete, the release record identifies the exact source code revision and built version of each application component. Production deployment from protected **`main`** uses those recorded versions. Merging code into `main` does not, by itself, authorize deployment.

- A release covers the frontend, API instances, background worker, scheduled work, and **database migrations** (controlled changes to database structures, such as tables and columns).

- During a Render deployment, the previous and new application versions may run simultaneously. Database migrations must therefore remain compatible with both versions during the rollout. Reverting to an earlier application version does not reverse database migrations or completed Stripe transactions; those changes require separate recovery handling.

- The first production launch remains isolated from ordinary public traffic during preparation. Subsequent releases use Render's deployment process and the API readiness check described below.

### 5.2 API health and rollout behavior

The FastAPI backend exposes two health-check endpoints that distinguish whether an instance can serve requests from whether its application process is running.

- **`/ready` — Readiness check:** Confirms that the API has completed startup and can connect to PostgreSQL. Render uses `/ready` as the Web Service's configured HTTP health check to determine whether an instance can receive traffic. Database connectivity is included because bookings and other application operations depend on PostgreSQL.

- **`/live` — Liveness check:** Confirms that the API process is running without checking PostgreSQL or external services. Operators use it to distinguish a stopped application process from one that is running but unable to reach a dependency. Render does not use `/live` for a separate routing or restart decision.

Render applies the following behavior when an instance already serving requests repeatedly fails `/ready`:

| Failure duration | Render behavior |
| --- | --- |
| **15 consecutive seconds** | Temporarily stops routing requests to the unhealthy instance |
| **60 consecutive seconds** | Restarts the instance |

- An unhealthy instance may continue receiving requests during the initial 15-second interval. During that interval, API requests must fail safely if PostgreSQL is unavailable.

- If PostgreSQL is unavailable, `/ready` can fail for both production instances because both depend on that database. Restarting an API instance does not restore database connectivity when PostgreSQL itself is unavailable.

- Render evaluates newly deployed instances before directing traffic to them. See the [Render health-check documentation](https://render.com/docs/health-checks) for the platform's routing and restart behavior.

### 5.3 Render service allocation

- Pickup Lane uses **one Render Pro workspace** containing separate staging and production services.

- The selected compute plans define the **central processing unit (CPU)** capacity and **random-access memory (RAM)** available to each running instance.

| Resource | Plan and capacity | Production allocation | Staging allocation |
| --- | --- | --- | --- |
| FastAPI Web Service | `1c-2g` — 1 CPU, 2 GB RAM | 2 API instances | 1 API instance |
| Background worker | `1c-2g` — 1 CPU, 2 GB RAM | 1 worker instance | 1 worker instance |
| Managed PostgreSQL | `1c-2g` — 1 CPU, 2 GB RAM, **100-connection limit** | 1 PostgreSQL database | 1 PostgreSQL database |
| Render Cron Job | `0.5c-512mb` — 0.5 CPU, 512 MB RAM | 1 Cron service | 1 Cron service |
| Render Static Site | Global CDN; no compute plan | 1 Static Site | 1 Static Site |

- Each managed PostgreSQL database has **5 GB of allocated storage**.

- The Render Pro workspace provides a **seven-day point-in-time recovery (PITR) window** for paid PostgreSQL databases. PITR allows a database to be restored to an available earlier point within that period. The separate S3 backup and recovery architecture is described in Section 6.

**Database connection capacity:** Each PostgreSQL service has a maximum of 100 concurrent connections shared by its clients. A **connection pool** maintains reusable database connections for an application process instead of opening a new connection for every operation.

- In production, the two API instances, background worker, Cron backup process, database migrations, and operational clients all consume connections from the same 100-connection limit. Staging has its own database and connection limit. Connection-pool sizes must account for the combined demand of these processes rather than treating the limit as available independently to each one.

- Staging normally runs one API instance but can temporarily run a second instance when testing the production deployment arrangement.

- **Cron execution limits:** Render permits only one active execution of a particular Cron Job at a time and stops an execution after 12 hours. This limitation applies to scheduled operations, including backup-related work assigned to Cron.

- Render's [compute-plan documentation](https://render.com/docs/compute-plans), [pricing](https://render.com/pricing), and [PostgreSQL recovery documentation](https://render.com/docs/postgresql-backups) provide the corresponding platform specifications.

### 5.4 Credentials and deployment access

- Render's built-in encrypted environment variables are the selected delivery mechanism for credentials used by the FastAPI Web Service, background worker, and Cron Job. Each service receives only its own environment's credentials required for its assigned responsibilities; the API, worker, and Cron Job do not automatically share unrestricted access. Render secret files are used only when a component genuinely requires file-based credentials. This mechanism is selected, but the credentials and grants have not yet been configured or verified.

- **Database migrations** receive their separate database credentials through the authorized migration execution and use a role with the permissions needed to modify database structures. Ordinary application processes use more restricted database roles.

- **GitHub Actions** uses protected, environment-specific deployment identities. Where supported, deployment access uses short-lived credentials instead of permanently stored credentials. Staging deployment access does not grant permission to deploy to production.

The React/Vite browser build receives only approved public configuration; no backend secret is supplied to it.

---

## 6. Data protection and recovery

### 6.1 Recovery architecture

Pickup Lane uses two database recovery mechanisms:

- **Render PostgreSQL point-in-time recovery (PITR):** The primary recovery option when Render's managed recovery service remains available. Pickup Lane can use it to restore an earlier database state after a recoverable database failure.
- **Independent PostgreSQL backups in Amazon S3:** A separate recovery source when the original Render database or its managed recovery capabilities are unavailable, including a major hosting or regional failure. These backups allow PostgreSQL to be rebuilt independently of the original database.

The S3 backups are stored database copies, not a continuously synchronized standby database.

Pickup Lane has two recovery objectives:

- **Recovery-point objective (RPO):** The maximum amount of data that may be lost, measured by the age of the newest usable recovery point.
- **Recovery-time objective (RTO):** The maximum time allowed to restore the application to a state where public traffic can safely resume.

**Recovery objectives**

Pickup Lane's recovery design establishes two limits: how much essential data can be lost during a failure and how long the application can take to return to safe operation.

| Objective | Target | What it means for Pickup Lane |
| --- | --- | --- |
| **Recovery-point objective (RPO)** | **Maximum 1 hour of data loss** | If a failure occurs, the newest usable recovery point for essential data must be no more than one hour older than the failure. This includes catastrophic database loss. |
| **Recovery-time objective (RTO)** | **Maximum 8 hours to restore service** | Once recovery is formally declared, Pickup Lane must restore the required systems and safely resume public traffic within eight hours. Restoring the database alone is not sufficient. |
| **Preferred recovery-point freshness** | **Approximately 15 minutes** | For ordinary database incidents where a suitable recovery mechanism remains available, Pickup Lane aims to recover a more recent database state, approximately 15 minutes before the failure. This is an aspiration, not a guaranteed recovery objective. |

The **one-hour data-loss limit and eight-hour recovery-time limit are required launch objectives**. The 15-minute preference does not replace or weaken either requirement.

These objectives describe what the recovery architecture must achieve, **not performance that has already been demonstrated**. The selected backup and restoration mechanisms still need to be verified against the required limits.

**Venue-image recovery:** Venue images are treated as replaceable assets rather than being assigned the same loss limits as essential transaction records. Pickup Lane uses R2 object-reference checks to identify missing images, displays a default image when necessary, and permits authorized administrators to replace missing files. PostgreSQL references must remain consistent with the images available after recovery.

### 6.2 Independent backups and regional placement

The existing **Render Cron Job** initiates compressed, consistent PostgreSQL full exports every **30 minutes** as the initial backup schedule.

These are **logical exports**, which capture the database's contents at a consistent point in time rather than copying its underlying storage files. They provide independent copies from which Pickup Lane can rebuild PostgreSQL if the original database cannot be recovered. Creating exports frequently is intended to limit how much recent data could be lost.

**Backup creation and storage**

The backup process reads PostgreSQL through a separate, restricted database role. Completed exports are encrypted during transfer and storage, uploaded to private S3 storage in **Ohio (`us-east-2`)**, and replicated asynchronously to **Oregon (`us-west-2`)**.

Each backup includes:

- **Source-state metadata:** Information identifying the database state captured by the export, including the time that state represents. This matters because a backup uploaded at 3:00 PM might contain database data from an earlier time. Recovery-point freshness is measured using the captured database state, not simply the upload time.
- **Checksum:** A calculated value used to detect whether backup contents have changed or become corrupted during storage or transfer.
- **Execution and completion records:** Information identifying expected backup runs, completed exports, uploads, and replication results so missing, incomplete, or delayed backups can be detected.

A completed export or matching checksum does not, by itself, prove that the database can be successfully restored. A **verified recovery point** requires a complete backup that can be restored and checked for the required data and database integrity. An Ohio backup does not become an available Oregon recovery copy until its replication is complete and that copy is verified as usable.

**Backup storage and protection**

The backup-storage configuration includes:

- **Retention:** Frequent exports remain for **48 hours**, with **one daily copy retained for 30 days**.
- **Access separation:** Backup writers, replication processes, recovery readers, and administrators use separately restricted permissions. Backup writers can create authorized backup objects but do not receive unrestricted deletion privileges. Ordinary application credentials cannot modify or delete protected backups.
- **S3 Versioning:** Preserves multiple versions of stored backup objects, allowing earlier versions to remain available when an object is replaced or a deletion is requested.
- **S3 Object Lock:** Protects retained object versions against deletion or modification during their configured retention periods.
- **Delete-marker protection:** A delete marker is an S3 record that makes an object appear deleted without necessarily destroying its earlier stored versions. Because such a marker could hide a protected backup from normal retrieval, **delete-marker replication from Ohio to Oregon is disabled**.

Backup retention and Object Lock settings must remain compatible with applicable legal retention and deletion obligations.

**Limitations of scheduled exports**

The 30-minute export schedule does not guarantee that Pickup Lane can always recover data less than one hour old. Exports require time to complete, upload, replicate, and validate. These delays can make the newest usable Oregon recovery point older than the backup schedule suggests.

Logical exports also cannot independently recover database changes made after the state they captured.

PostgreSQL uses a **write-ahead log (WAL)** to record database changes. With a compatible physical database backup and archived WAL records, those changes can be replayed to recover a database state more recent than the underlying backup.

**Logical exports cannot serve as the physical backup required for WAL replay.** Therefore, the selected independent full-export arrangement does not, by itself, provide continuous point-in-time recovery.

If exports and replication cannot satisfy the required one-hour data-loss objective, Pickup Lane will need a compatible point-in-time recovery mechanism or another verified recovery approach. The required objective cannot simply be relaxed.

Export duration, backup growth, replication delays, and actual restoration performance remain unverified.

### 6.3 Regional restoration and protected decisions

The Oregon backup copies provide an independent recovery source if Ohio infrastructure becomes unavailable.

Regional restoration requires rebuilding PostgreSQL and the dependent application services, then reconciling restored records with Stripe payments, Firebase identity information, background jobs, and R2 image references.

This reconciliation is necessary because the restored database may represent an earlier point in time than the records retained by external services. For example, Stripe may have completed a payment after the database backup was created. The restored application must account for that payment rather than incorrectly treating it as unfinished or processing it again.

**State-changing public requests**, including those affecting bookings, payments, or account records, remain disabled until the restored system is safe to operate.

**Protected decision journal**

Restoring an older database backup creates an additional risk: it can reverse important decisions made after that backup.

For example, suppose Pickup Lane creates a database backup at 2:30 PM and completes an approved account deletion at 2:45 PM. Restoring the 2:30 PM backup could bring back records that should remain deleted.

Pickup Lane therefore uses an independently recoverable **decision journal** to preserve approved account deletions, retention pauses, and legal or security holds that must remain effective after database restoration.

The journal is stored directly in an access-restricted, versioned location within the existing **Oregon S3 recovery storage**, separately from replicated database backups. Writing directly to Oregon allows those decisions to be protected without waiting for the asynchronous replication of Ohio database exports.

Each journal entry contains:

- **Stable operation identifier:** A unique identifier that allows Pickup Lane to recognize a previously recorded decision, including after an interrupted operation, without accidentally applying it twice.
- **Verifiable ordering:** A recorded sequence establishing the order of decisions affecting the same record. This prevents restoration from applying a later decision before an earlier decision on which it depends.
- **Approval and completion states:** Separate records identifying when a decision was authorized and when its associated action was confirmed to have been carried out.

**Decision protection and completion**

The journal distinguishes two states:

- **Approval:** The decision is recorded and its protected availability in Oregon is confirmed before it is acknowledged as accepted or protected as a finalized decision.
- **Completion:** The journal records that the approved action has been carried out and its result is known; completion is not reported without the required Oregon confirmation.

Before a decision is acknowledged as accepted, completed, or protected as finalized, its journal entry must be successfully written and read back from Oregon. If that write or readback fails or is uncertain, a pending account deletion still retains its committed local inactive state and durable work and denies protected backend operations.

If an operation is interrupted or its outcome is uncertain, the recorded identifier and state are used to determine whether the action occurred before it is repeated or marked complete.

If Oregon is unavailable, the affected decision cannot be acknowledged as protected or reported complete. An unresolved legal or security hold prevents conflicting actions until its state is established.

**Journal use during restoration**

After PostgreSQL is restored, Pickup Lane applies relevant journal decisions that are missing from the recovered database.

This prevents an older database backup from silently reversing completed account deletions, retention pauses, or legal and security holds.

Missing journal entries, uncertain operation outcomes, or unresolved ordering prevent state-changing production traffic from resuming.

Journal-writing and recovery-reading permissions are separate from permissions to modify or delete database backups.

**Additional recovery materials**

Recovery materials include application service definitions, database schema migrations, release artifacts, non-secret external-service configurations, DNS records, backup metadata, and instructions for restoring authorized administrative and service access.

Credentials are recreated or securely restored through their designated mechanisms; their secret values are not stored in this architecture document.

---

## 7. Monitoring and product analytics

### 7.1 Operational observability

**Grafana Cloud Pro** provides Pickup Lane's operational monitoring by collecting and displaying application logs, performance metrics, and alerts. Logs record events and errors, while metrics measure system behavior, such as response times, database connection usage, and background-job delays.

**FastAPI and the background worker** use **OpenTelemetry (OTel)**, an open standard and set of tools for generating and sending monitoring data, to send sanitized application logs and metrics to their respective Grafana Cloud stacks. Each environment uses its own monitoring-data ingestion credentials, dashboards, and alert configurations. Ingestion credentials authorize an application to send monitoring data to Grafana.

Pickup Lane monitors the following operational signals:

- **Application performance:** API response times, application errors, database connection pressure, and failures encountered when communicating with external services.
- **Background operations:** Job backlogs, stalled workers, failed operations, missed scheduled work, and payment-reconciliation problems.
- **Backup and recovery health:** Completed database exports, backup freshness, Ohio-to-Oregon replication delays, and protected decision-journal failures.
- **Independent availability:** External monitoring checks whether the public API is reachable, including when FastAPI cannot send its own monitoring data.

**Render diagnostics:** Render retains its own runtime logs, deployment records, and platform diagnostics separately from Grafana. The selected Render Pro workspace provides **14 days of native log retention**. These records are not automatically forwarded into the three Grafana stacks.

Other external services retain operational records through their own systems. Their records are not treated as Grafana monitoring data unless a specific collection or reporting connection has been established.

**Incident response:** Grafana Incident Response & Management (IRM) routes production alerts to designated responders through configured notifications and escalation arrangements. The initial subscription includes **three monthly active IRM users**, with additional users subject to usage charges. Development and staging alerts remain separate from production incident notifications.

**Browser error reporting:** The React frontend sends a restricted set of diagnostic error reports to a FastAPI browser-error endpoint. FastAPI validates the permitted information before forwarding it to the corresponding Grafana stack. Private Grafana ingestion credentials remain on the backend and are not exposed to the browser.

Monitoring data excludes secrets, payment credentials, private messages, and other sensitive information unnecessary for diagnosis. **Metric labels**—categories attached to measurements, such as service name or error type—use a restricted set of permitted values. This prevents monitoring from generating excessive numbers of distinct measurements, which can increase storage and processing costs.

### 7.2 Product analytics

**PostHog Pay-as-you-go** provides Pickup Lane's product analytics, measuring how visitors use selected application features. Development, staging, and production have separate PostHog projects under one billing organization.

Pickup Lane manually records only five event classes:

1. **Game discovery**
2. **Game view**
3. **Completed registration**
4. **Community-game creation**
5. **Completed booking**

These events are generated explicitly by application code rather than through automatic collection of website activity. Their exact triggers, permitted data fields, and handling of repeated events must be defined and approved before collection is enabled. Selecting an event category does not, by itself, authorize collecting it.

- **Permission-based collection:** PostHog collection starts disabled in every environment. It begins only after the visitor provides affirmative permission and the required privacy disclosures and collection configuration are approved. Withholding permission prevents analytics collection; withdrawing permission stops subsequent collection and clears applicable locally stored analytics information.
- **Disabled automatic features:** Automatic click and form tracking, session recording and replay, automatic pageviews, and automatic pageleaves remain disabled. Other unapproved automatic collection and unrelated paid PostHog products are not enabled.
- **Environment separation:** Each environment sends approved events exclusively to its corresponding PostHog project.
- **Data protection:** Analytics events exclude sensitive personal information, payment credentials, raw financial fields, private messages, and other sensitive user content. Automatically added information, such as page addresses, referral information, and browser or network identifiers, must also remain within the approved collection scope.

PostHog analytics is used to understand application usage, not as the authoritative record of bookings, payments, or other business transactions.

Visitor permission alone does not establish compliance with applicable privacy laws or determine how previously collected data is retained or deleted. Those arrangements depend on Pickup Lane's approved privacy and data-retention controls.

---

## 8. Monthly infrastructure cost model

This cost model estimates the recurring monthly charges for Pickup Lane's selected infrastructure, using the service allocations in Section 5 and one Render Pro workspace shared by staging and production.

The **modeled monthly baseline** is the minimum recurring cost of the selected plans and allocated resources, assuming they remain provisioned for a full month. It excludes charges that depend on actual usage, such as bandwidth, backup storage, and additional Cron execution time.

These figures are planning estimates, not verified invoices or spending limits.

### 8.1 Render cost breakdown

| Render service / charge | Monthly unit rate | Quantity / calculation | Monthly subtotal |
|---|---|---|---:|
| Render Pro workspace, shared across staging and production | $25/month | 1 × $25 | $25.00 |
| Production FastAPI `1c-2g` | $25/instance-month | 2 × $25 | $50.00 |
| Production worker `1c-2g` | $25/instance-month | 1 × $25 | $25.00 |
| Production PostgreSQL `1c-2g` | $40/month | 1 × $40 | $40.00 |
| Production PostgreSQL storage | First 1 GB included; $0.30/additional GB-month | (5 − 1) × $0.30 | $1.20 |
| Production Cron `0.5c-512mb` | $0.00016/active minute; $1 minimum | 1 Cron service; minimum charge | $1.00 |
| Production Static Site | $0 fixed compute | 1 Static Site | $0.00 |
| **Production subtotal** | | | **$117.20** |
| Staging FastAPI `1c-2g` | $25/instance-month | 1 × $25 | $25.00 |
| Staging worker `1c-2g` | $25/instance-month | 1 × $25 | $25.00 |
| Staging PostgreSQL `1c-2g` | $40/month | 1 × $40 | $40.00 |
| Staging PostgreSQL storage | First 1 GB included; $0.30/additional GB-month | (5 − 1) × $0.30 | $1.20 |
| Staging Cron `0.5c-512mb` | $0.00016/active minute; $1 minimum | 1 Cron service; minimum charge | $1.00 |
| Staging Static Site | $0 fixed compute | 1 Static Site | $0.00 |
| **Staging subtotal** | | | **$92.20** |
| **Total Render monthly baseline** | | $25 workspace + $117.20 production + $92.20 staging | **$234.40** |

An **instance-month** represents the cost of running one compute instance for a full month. A **GB-month** measures allocated database storage over a month; both PostgreSQL databases are modeled with 5 GB each.

**Render Pro workspace allowances**

The selected workspace includes:

- **25 GB of outbound bandwidth:** Data transferred from Render services to users or other destinations outside Render. Usage beyond this allowance costs **$0.15 per GB**.
- **1,000 Starter build-pipeline minutes:** Time used by Render to build and prepare application deployments. Additional usage costs **$5 per 1,000 minutes**.
- **15 custom domains:** Additional domains cost **$0.25 per domain per month**.

These allowances are shared across the Render workspace rather than assigned separately to staging and production.

**Cron billing:** Each Cron service costs the greater of **$1 per month** or **$0.00016 multiplied by its total active execution minutes**. The table uses the $1 minimum for each service. The production backup schedule described in Section 6 can cause charges above that minimum depending on how long backup runs and other scheduled tasks execute.

Static Sites have no fixed compute charge, but their applicable bandwidth and build activity contribute to workspace usage.

### 8.2 Modeled recurring-charge summary

| Provider | What the modeled charge covers | Modeled monthly minimum |
|---|---|---:|
| Render Pro and application services | One workspace and the staging and production resources itemized in Section 8.1 | $234.40 |
| Postmark Basic | One subscription with 10,000 shared monthly emails and up to five sending servers | $15.00 |
| Grafana Cloud Pro with IRM | One paid monitoring subscription supporting the three selected Grafana stacks and up to three monthly active IRM users within the included allowance | $19.00 |
| **Total modeled recurring-charge baseline** | | **$268.40** |

Postmark's included email volume is shared across its development, staging, and production sending servers.

Grafana's three stacks share the account's included monitoring allowances. Additional monitoring usage or active users beyond the subscription allowances can generate charges.

The summary contains only the recurring charges included in the model. It does not assume that services omitted from this table will have zero actual cost.

### 8.3 Usage-dependent and separately billed costs

The following expenses are not included in the $268.40 baseline:

- **Render:** Usage above the workspace allowances, additional database storage, Cron execution above the minimum, compute changes, temporary deployment overlap, and recovery-related resources.
- **Cloudflare R2:** Image storage, storage operations, and other billable usage beyond applicable free allowances.
- **Amazon S3:** Ohio and Oregon backup storage, cross-region replication, protected object versions, decision-journal storage and requests, and recovery-related operations.
- **Firebase Identity Platform and reCAPTCHA:** Billable authentication usage, assessments, and any enabled capabilities outside applicable free allowances.
- **PostHog Pay-as-you-go:** Analytics usage or enabled products that exceed included allowances.
- **Grafana Cloud:** Log and metric ingestion, browser-error telemetry, monitoring checks, active users, and other billable usage beyond the included subscription allowances.
- **GitHub Actions:** No fixed charge is modeled for eligible public-repository standard runners. Paid runners, additional storage, or other billable CI features are separate.
- **Registrar, DNS, Stripe, and taxes:** Domain registration and DNS charges where applicable, Stripe transaction fees, and applicable taxes.

**Budget comparison**

| Cost measure | Monthly amount |
|---|---:|
| Approved infrastructure planning ceiling | **$195.00** |
| Modeled recurring-charge baseline | **$268.40** |
| **Amount above ceiling** | **$73.40** |

The modeled baseline already exceeds Pickup Lane's monthly infrastructure budget ceiling by **$73.40**, before usage-dependent and separately billed charges.

The current configuration therefore does not fit within the approved budget. Meeting the ceiling would require a separate cost or infrastructure decision; this cost model does not assume any previously selected service or resource has been removed.
<hr>

## 9. Operational ownership and configuration boundaries

### 9.1 Responsibility coverage

- Pickup Lane's architecture identifies **14 areas of operational responsibility**. Each area requires an accountable person responsible for its operation, security, or recovery.

#### Responsibility areas

- The responsibilities are grouped as follows:

- **Delivery and application:** Production-readiness program; platform and deployment; API; frontend; release assurance; durable background jobs.
- **Data and external services:** Identity and application security; PostgreSQL; Stripe and financial operations; Cloudflare R2; secrets and external-service access.
- **Reliability and governance:** Monitoring and reliability; incident recovery; privacy and retention.

#### Alternate recovery coverage

- **Alternate recovery coverage** spans 10 areas: registrar and DNS; repository and continuous integration (CI); Firebase; Stripe; Cloudflare R2; PostgreSQL hosting; application hosting; monitoring; backups; and incident-command recovery.

- These alternate recovery arrangements provide a way to regain control of critical systems when the primary responsible person or their credentials are unavailable. Recovery coverage must include the ability to perform the necessary recovery work, not merely regain access to a provider account.

- The responsibility categories define the required coverage. They do not mean that specific individuals have already accepted these responsibilities or that their recovery access has been verified.

#### Provider administration

- Human administrators use individually attributable, multifactor authentication (MFA)-protected accounts. Emergency administrative access is separate from the credentials used by running application services. This allows authorized recovery personnel to manage critical services without granting routine application processes administrator privileges.

### 9.2 Application configuration inventory

- Pickup Lane uses **configuration keys**—named settings that control how application components connect to services, enforce limits, and select environment-specific behavior without embedding those values directly into application code.

- The following tables identify the recorded configuration keys, the components that use them, and their purposes.

#### Credential handling

- **Backend configuration** is supplied privately to the appropriate application services. Secret credentials are stored in environment-specific configuration rather than in this architecture document.

#### Browser configuration

- **Frontend configuration** uses Vite's `VITE_` prefix to make selected values available to the browser when the frontend is built. These values are publicly accessible and must contain only information approved for browser exposure. The prefix does not make a secret safe to publish.

#### Database connections and query limits

These settings control database connections and limits for API, worker, and scheduled processes. Database migrations and automated tests use separate connection settings appropriate to their access requirements.

| Configuration key | Consumer / scope | Purpose and exposure |
|---|---|---|
| `DATABASE_URL` | API, worker, scheduler | Private connection information for the environment's application database |
| `MIGRATION_DATABASE_URL` | Database migrations; migration-lifecycle tests | In staging and production, the private migration connection with permissions needed for authorized schema changes, separate from ordinary application roles. In automated tests and CI, the dedicated migration-lifecycle test database. Local development may omit it, in which case migrations use `DATABASE_URL` |
| `TEST_DATABASE_URL` | Local development / CI | Connection to an isolated test database |
| `DB_POOL_SIZE` | Backend database clients | Number of reusable database connections maintained in each configured connection pool |
| `DB_MAX_OVERFLOW` | Backend database clients | Maximum additional temporary connections allowed beyond the configured pool size |
| `DB_POOL_WAIT_TIMEOUT_SECONDS` | Backend database clients | Maximum time a request waits for an available pooled connection |
| `DB_STATEMENT_TIMEOUT_MILLISECONDS` | Backend database clients | Maximum permitted SQL statement execution time |
| `DB_LOCK_TIMEOUT_MILLISECONDS` | Backend database clients | Maximum time a database operation may wait to acquire a required lock |

The connection settings must account for the shared PostgreSQL connection limit described in Section 5.3.

#### Firebase — backend identity and App Check

These settings connect backend identity operations and App Check verification to the Firebase resources assigned to each environment. Administrator credential material remains private.

| Configuration key | Consumer / scope | Purpose and exposure |
|---|---|---|
| `FIREBASE_ADMIN_CREDENTIALS_JSON` | Backend | Private Firebase administrator credential material supplied in JSON format |
| `FIREBASE_ADMIN_CREDENTIALS` | Backend / local development | Private administrator credentials or a local, version-control-ignored credential-file path |
| `FIREBASE_PROJECT_ID` | Backend | Identifies the Firebase project assigned to the environment |
| `FIREBASE_APP_CHECK_MODE` | Backend | Selects the configured App Check handling mode |
| `FIREBASE_APP_CHECK_APP_ID` | Backend | Identifies the Firebase application associated with App Check |
| `FIREBASE_HTTP_TIMEOUT_SECONDS` | Backend | Maximum configured timeout for Firebase HTTP requests |

#### Firebase — public browser configuration

The Vite frontend uses these settings to connect to the correct Firebase project and initialize its browser-side identity and App Check integration. The values are public client configuration, not Firebase administrator credentials.

| Configuration key | Consumer / scope | Purpose and exposure |
|---|---|---|
| `VITE_FIREBASE_API_KEY` | Frontend build | Public Firebase client API key |
| `VITE_FIREBASE_AUTH_DOMAIN` | Frontend build | Firebase authentication domain |
| `VITE_FIREBASE_PROJECT_ID` | Frontend build | Identifies the Firebase project used by the frontend |
| `VITE_FIREBASE_STORAGE_BUCKET` | Frontend build | Firebase client configuration identifier; does not select Firebase Storage for Pickup Lane's venue images |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | Frontend build | Firebase messaging sender identifier used in the client configuration |
| `VITE_FIREBASE_APP_ID` | Frontend build | Identifies the registered Firebase web application |
| `VITE_FIREBASE_MEASUREMENT_ID` | Frontend build | Firebase client configuration identifier; does not enable a separate Firebase Analytics integration |
| `VITE_FIREBASE_APP_CHECK_MODE` | Frontend build | Selects browser-side App Check behavior |
| `VITE_FIREBASE_APP_CHECK_RECAPTCHA_ENTERPRISE_SITE_KEY` | Frontend build | Public reCAPTCHA Enterprise site key used for the selected App Check integration |

Cloudflare R2 remains Pickup Lane's venue-image storage service, and PostHog remains its product analytics service. The presence of Firebase client identifiers does not introduce additional storage or analytics services.

#### Stripe payments

These settings bind payment operations and webhook verification to the Stripe environment assigned to Pickup Lane. Stripe secret credentials remain on the backend; publishable keys are permitted in browser configuration.

| Configuration key | Consumer / scope | Purpose and exposure |
|---|---|---|
| `STRIPE_SECRET_KEY` | Backend | Private Stripe API credential |
| `STRIPE_WEBHOOK_SECRET` | Backend webhook | Private secret used to verify Stripe webhook signatures |
| `STRIPE_PUBLISHABLE_KEY` | Backend configuration | Stripe publishable key; not a private payment credential |
| `STRIPE_CURRENCY` | Backend | Configured payment currency |
| `ENABLE_STRIPE_PAYMENTS` | Backend | Controls the backend payment feature setting |
| `STRIPE_READ_TIMEOUT_SECONDS` | Backend | Timeout for Stripe read operations |
| `STRIPE_MUTATION_TIMEOUT_SECONDS` | Backend | Timeout for Stripe operations that create or change payment-related records |
| `VITE_STRIPE_PUBLISHABLE_KEY` | Frontend build | Public Stripe key for the assigned environment |
| `VITE_ENABLE_STRIPE_PAYMENTS` | Frontend build | Public frontend payment feature setting |

The frontend feature setting does not replace backend payment authorization or access controls.

#### Cloudflare R2 object storage

These settings support the private-image and published-image storage arrangement established in Section 2.5.

The backend uses private-origin credentials for authorized image uploads and separate publication credentials for processed images. The **four `R2_PUBLIC_*` configuration keys** describe the selected publication design but are not yet implemented in application code.

| Configuration key | Consumer / scope | Purpose and exposure |
|---|---|---|
| `R2_ACCESS_KEY_ID` | Backend | Private-origin bucket access-key identifier; private |
| `R2_SECRET_ACCESS_KEY` | Backend | Private-origin bucket access secret; private |
| `R2_ACCOUNT_ID` | Backend | Identifies the configured Cloudflare R2 account |
| `R2_BUCKET_NAME` | Backend | Name of the private-origin storage bucket |
| `R2_PUBLIC_BUCKET_NAME` | Backend | Name of the separate published-image bucket; planned binding |
| `R2_PUBLIC_ACCESS_KEY_ID` | Backend | Published-image bucket access-key identifier; private, planned binding |
| `R2_PUBLIC_SECRET_ACCESS_KEY` | Backend | Published-image bucket access secret; private, planned binding |
| `R2_PUBLIC_BASE_URL` | Backend | Base address for published images; production uses its configured custom domain; planned binding |
| `R2_ENDPOINT_URL` | Backend | Endpoint used for R2 storage operations |
| `R2_UPLOAD_URL_MINUTES` | Backend | Validity period for authorized signed upload URLs |
| `R2_READ_URL_MINUTES` | Backend | Validity period for signed object-read URLs where permitted |
| `R2_MAX_IMAGE_BYTES` | Backend | Maximum accepted image-file size |
| `R2_ALLOWED_IMAGE_TYPES` | Backend | Image-file types accepted for processing |
| `R2_OBJECT_CONNECT_TIMEOUT_SECONDS` | Backend | Maximum configured connection-establishment time for R2 operations |
| `R2_OBJECT_READ_TIMEOUT_SECONDS` | Backend | Timeout for reading objects from R2 |

Private R2 access credentials remain on the backend. The published-image base URL identifies where approved public images are served; it does not grant permission to access private originals.

#### R2 isolated provider-contract tests

These settings are used by isolated tests that communicate with R2 to verify the storage integration against actual provider behavior. They are separate from the credentials used for production image storage.

| Configuration key | Consumer / scope | Purpose and exposure |
|---|---|---|
| `R2_TEST_ACCOUNT_ID` | Isolated tests | R2 account identifier assigned to testing |
| `R2_TEST_ACCESS_KEY_ID` | Isolated tests | Private access-key identifier for test operations |
| `R2_TEST_SECRET_ACCESS_KEY` | Isolated tests | Private access secret for test operations |
| `R2_TEST_BUCKET_NAME` | Isolated tests | Storage bucket used for isolated R2 tests |
| `R2_TEST_ENDPOINT_URL` | Isolated tests | R2 endpoint used by the test integration |

These settings do not authorize ordinary CI jobs to access production R2 resources.

#### Application environment, HTTP, and token signing

These settings govern application environment selection, incoming HTTP requests, browser access to the API, and a private token-signing secret.

Request-body limits control the maximum amount of data accepted by different API endpoints. **JSON (JavaScript Object Notation)** is the text-based data format used for ordinary structured request bodies.

| Configuration key | Consumer / scope | Purpose and exposure |
|---|---|---|
| `APP_ENV` | Backend | Identifies the application environment |
| `ALLOWED_HOSTS` | Backend | Lists HTTP hostnames accepted by the backend |
| `CORS_ALLOWED_ORIGINS` | Backend | Lists website origins permitted by the configured CORS policy |
| `ENABLE_API_DOCS` | Backend | Controls exposure of API documentation |
| `ENABLE_DB_HEALTH` | Backend | Configures database-health checking behavior |
| `ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES` | Backend | Maximum accepted size of ordinary JSON request bodies |
| `PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES` | Backend | Maximum accepted size of platform-notification request bodies |
| `STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES` | Backend webhook | Maximum accepted size of Stripe webhook request bodies |
| `VITE_API_BASE_URL` | Frontend build | Public base URL used by the browser to reach the FastAPI backend |
| `INBOX_TOKEN_SECRET` | Backend | Private secret used to sign application inbox tokens |

The public `VITE_API_BASE_URL` identifies the API's address; it does not authorize access to protected API operations.

#### Additional provider configuration

- The application also depends on environment-specific access and configuration for AWS S3 backups, replication and the protected decision journal; Postmark sending servers; Grafana ingestion and IRM administration; PostHog projects; GitHub deployment identities; Render administration; and domain, DNS, and HTTPS certificate management.

- These systems use credentials and permissions appropriate to their individual responsibilities. They do not reuse Firebase, Stripe, or R2 application secrets.

- The tables above preserve the recorded application configuration-key names. They do not invent additional environment-variable names for external systems whose exact configuration keys have not yet been specified.
