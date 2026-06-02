# Aegis demo — how it actually works

## Two surfaces (your model)

| Page | Who it's for | What runs |
|------|----------------|-----------|
| **Draft an appeal** (`/appeal`) | The **customer** (you, live) | **Real** backend every time — real letter, real librarian |
| **How Aegis learns** (`/showcase`) | **Judges** — behind the scenes | **Recorded** v1 vs v3 evidence from your eval runs |

You play the customer on `/appeal`. You switch to `/showcase` to show judges what happened under the hood.

## Recording the Devpost video

1. Start the backend (`./scripts/dev.sh` or Cloud Run).
2. Open **Settings** → confirm **Connected** → **Save**.
3. On **Draft an appeal**: paste or pick a sample case → submit → real draft.
4. Switch nav to **How Aegis learns** → pick the same case → show v1/v3 lift.
5. Screen-record that flow.

No “practice mode” on the customer path — if the backend is down, you get an error (honest).

## Settings (only if needed)

- **Service address** — where the backend lives.
- **Trusted source lookup** — on by default when connected; thin library → up to 5 trusted fetches.
