# pgAdmin Setup and Database Connection Guide

This guide explains how to start and connect to the local PostgreSQL database using the pgAdmin 4 Docker container included in this project.

## 1. Start the pgAdmin Container

pgAdmin is in the `dev` profile, so a plain `docker compose up` does not start it. Start it explicitly from the project root:

```bash
docker compose --profile dev up -d pgadmin
```

It listens on `127.0.0.1` only, so it is reachable from this machine and not from the network. Postgres itself publishes no host port; pgAdmin reaches it over the internal `livocrm` Docker network.

## 2. Log In to pgAdmin

1. Open your web browser and navigate to: **http://127.0.0.1:5050**
2. Log in with the credentials you set in your local `.env` (never commit them):
   * **Email**: `PGADMIN_DEFAULT_EMAIL`
   * **Password**: `PGADMIN_DEFAULT_PASSWORD`

## 3. Register the LivoCRM Database Server

Once you are logged into the pgAdmin dashboard, you need to tell it how to connect to the `db` container.

1. In the top-left tree menu, right-click on **Servers**.
2. Select **Register** → **Server...**
3. A dialog window will appear. Fill it out as follows:

### General Tab
* **Name**: Type a descriptive name, e.g., `LivoCRM`

### Connection Tab
Fill in these details exactly as shown (these match your `.env` variables):

| Field | Value | Notes |
|---|---|---|
| **Host name/address** | `db` | **Crucial:** Use the Docker service name (`db`), not `localhost`. pgAdmin resolves this internally on the `livocrm` Docker network. |
| **Port** | `5432` | Inside the Docker network, PostgreSQL listens on its native port. |
| **Maintenance database** | `livocrm` | |
| **Username** | `livocrm_user` | |
| **Password** | value of `POSTGRES_PASSWORD` in `.env` | `change-me` in `.env.example` is a placeholder; generate your own. |
| **Save password** | ✅ (Checked) | Toggle on so you don't have to re-enter it. |

4. Click the **Save** button.

## 4. Viewing Your Data

To browse your tables and view data:

1. In the left panel, expand the tree: 
   **Servers** → **LivoCRM** → **Databases** → **livocrm** → **Schemas** → **public** → **Tables**.
2. You will see a list of your application's tables (e.g., `deals`, `contacts`, `users`).
3. Right-click any table name and select **View/Edit Data** → **All Rows** to view and modify the records.
