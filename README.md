# gpt-manifold

![gpt-manifold](logo.png)

An assistant for betting on prediction markets on [manifold.markets](https://manifold.markets), utilizing OpenAI's GPT APIs.

### Run

`pip install gpt_manifold`

`python -m gpt_manifold`

The assistant will display a list of markets and guide you through the process of placing bets.

### Features

- Display interactive list of markets and market information
- Generate `YES`, `NO` or `ABSTAIN` prediction using selected model (`gpt-4`, `gpt-3.5-turbo`)
- Use maximum amount of mana specified by user
- Post comment explaining reasoning (please don't abuse this!)
