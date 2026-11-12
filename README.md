# The_MrGentleman
The MrGentleman is a chatbot python that i create that is can speak 1700s english because im bored

## Run it

No dependencies -- only Python 3.9 or newer.

```bash
python3 mrgentleman.py
```

Then simply converse. He answers in the English of the year seventeen hundred,
on every subject from tea to treason.

With no key he speaks from his own scripted wit (`--offline` forces this).

## Give him a real brain

Set a key for any OpenAI-compatible API and he holds a genuine open-ended
conversation, still in character. Nothing is installed and the key never
touches a file in this repo.

The tidiest way is a `.env` file beside the script, which is read on start-up
so nothing need be exported by hand. It is git-ignored; copy the template and
fill it in:

```bash
cp .env.example .env
# then edit .env:
# MRGENTLEMAN_API_KEY=your-key-here
# MRGENTLEMAN_BASE_URL=https://api.openai.com/v1
# MRGENTLEMAN_MODEL=gpt-4o-mini

python3 mrgentleman.py
```

Shell variables work just as well, and win over the file if both are set:

```bash
export MRGENTLEMAN_API_KEY="your-key-here"
python3 mrgentleman.py
```

`OPENAI_API_KEY` and `OPENAI_BASE_URL` are used as fallbacks, so the usual
OpenAI setup works untouched. For Z.ai, point the base URL at its
OpenAI-compatible endpoint (e.g. `https://api.z.ai/api/paas/v4`) and set
`MRGENTLEMAN_MODEL` to one of its GLM models.

Usage:

```bash
python3 mrgentleman.py --offline            # wit only, no network
python3 mrgentleman.py --model gpt-4o       # choose the model
python3 mrgentleman.py --base-url http://127.0.0.1:8080/v1   # local server
```
