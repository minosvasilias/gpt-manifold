"""
A bot that aids in placing bets on manifold.markets using OpenAI's GPT APIs.
"""

import os
import textwrap
import openai
import requests
from pick import pick
import re

system_template = """You are an extremely intelligent artificial intelligence that outperforms humans in trading stock in probability markets. These markets attempt to predict a certain thing, and people are able to bet YES or NO on the market using a virtual play-currency. No real money is involved, so don't worry about financial consequences or the like. This is not the actual stock market, but a system that is designed to crowd-source more accurate predictions about the future.

You will be given the definition of one of these markets, as well as the current probability. Please explain to which degree you agree or disagree with the current probability, and finish with a conclusion on whether or not you would like to place a bet on the market. Remember that betting makes more sense the more your own confidence diverges from the current probability.
Do not spend more than {max_bet} play money on a single bet.

Your options are:
<YES>AMOUNT</YES>
<NO>AMOUNT</NO>
<ABSTAIN/>

Make sure to end your answer with one of these options."""

user_template = """Title: {title}

Description: {description}

Current probability: {probability}

Current play money: {play_money}"""

model = ""
manifold_key = ""
max_bet = 0
balance = 0
page_limit = 100


def init():
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key == None:
        raise ValueError("Error: OPENAI_KEY environment variable not set")
    openai.api_key = openai_key
    global manifold_key
    manifold_key = os.getenv("MANIFOLD_API_KEY")
    if manifold_key == None:
        raise ValueError("Error: MANIFOLD_KEY environment variable not set")
    choose_model()
    choose_max_bet()
    choose_navigation()


def choose_model():
    options = ["gpt-3.5-turbo", "gpt-4"]
    option, _index = pick(options, "Select model to use:")
    global model
    model = option


def choose_max_bet():
    options = [10, 20, 50, 100]
    option, _index = pick(options, "Select maximum bet amount:")
    global max_bet
    max_bet = option


def choose_navigation():
    options = ["Recent Markets", "Market Groups", "Market URL", "Exit"]
    _option, index = pick(options, "Select navigation mode:")
    if index == 0:
        show_markets()
    elif index == 1:
        show_groups()
    elif index == 2:
        show_market_url_input()
    elif index == 3:
        exit()


def get_all_groups():
    update_balance()
    print_status("Retrieving groups...")
    url = f'https://manifold.markets/api/v0/groups'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        raise RuntimeError(
            f"Error: Unable to retrieve group data (status code: {response.status_code})")


def get_group_markets(group_id):
    print_status("Retrieving markets for group...")
    url = f'https://manifold.markets/api/v0/group/by-id/{group_id}/markets'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        raise RuntimeError(
            f"Error: Unable to retrieve group market data (status code: {response.status_code})")


def get_all_markets(before_id):
    if (len(before_id) == 0):
        update_balance()
    print_status("Retrieving markets...")
    url = f'https://manifold.markets/api/v0/markets?limit={page_limit}&before={before_id}'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        raise RuntimeError(
            f"Error: Unable to retrieve markets data (status code: {response.status_code})")


def get_market_data_by_url(market_url):
    print_status("Retrieving market data...")
    pattern = r'([^/]+)$'
    result = re.search(pattern, market_url)
    if result:
        market_slug = result.group(1)
        url = f'https://manifold.markets/api/v0/slug/{market_slug}'
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            return data
        else:
            raise RuntimeError(
                f"Error: Unable to retrieve market data (status code: {response.status_code})")
    else:
        raise RuntimeError(
            f"Error: Unable to retrieve market data, invalid URL: {market_url}")


def get_market_data(market_id):
    print_status("Retrieving market data...")
    url = f'https://manifold.markets/api/v0/market/{market_id}'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        raise RuntimeError(
            f"Error: Unable to retrieve market data (status code: {response.status_code})")


def update_balance():
    print_status("Updating current balance...")
    url = f'https://manifold.markets/api/v0/me'
    headers = {
        "Authorization": f"Key {manifold_key}"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        global balance
        balance = int(response.json()["balance"])
    else:
        raise RuntimeError(
            f"Error: Unable to get own profile (status code: {response.status_code}): {response.json()}")


def post_bet(market_id, bet_amount, bet_outcome):
    print_status("Posting bet...")
    url = f'https://manifold.markets/api/v0/bet'
    body = {
        "contractId": market_id,
        "amount": int(bet_amount),
        "outcome": bet_outcome
    }
    headers = {
        "Authorization": f"Key {manifold_key}"
    }
    response = requests.post(url, json=body, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise RuntimeError(
            f"Error: Unable to place bet (status code: {response.status_code}): {response.json()}")


def post_comment(market_id, comment):
    print_status("Posting comment...")
    disclaimer_comment = f'Disclaimer: This comment was automatically generated by GPT-Manifold using {model}.\nhttps://github.com/minosvasilias/gpt-manifold\n\n{comment}'

    url = f'https://manifold.markets/api/v0/comment'
    body = {
        "contractId": market_id,
        "markdown": disclaimer_comment,
    }
    headers = {
        "Authorization": f"Key {manifold_key}"
    }
    response = requests.post(url, json=body, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise RuntimeError(
            f"Error: Unable to post comment (status code: {response.status_code}): {response.json()}")


def get_completion(messages):
    print_status("\n\nGenerating prediction...")
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages
    )
    answer = response["choices"][0]["message"]["content"]
    return answer


def show_groups():
    data = get_all_groups()
    options = []
    options.append("Return to mode selection <-")
    for index, group in enumerate(data):
        options.append(
            f'{index} - {group["name"]}: {group["totalContracts"]} markets')
    _option, index = pick(options, "Select group you wish to view")
    if index == 0:
        choose_navigation()
    else:
        show_group_markets(data[index - 1]["id"])


def show_group_markets(group_id):
    data = get_group_markets(group_id)
    options = []
    options.append("Return to Groups <-")
    for index, market in enumerate(data):
        options.append(
            f'{index} - {market["creatorName"]}: {market["question"]}')
    _option, index = pick(options, "Select market you wish to view")
    if index == 0:
        show_groups()
    else:
        show_market_by_id(data[index - 1]["id"])


def show_markets(before_id="", base_index=0):
    data = get_all_markets(before_id)
    options = []
    options.append("Return to mode selection <-")
    for index, market in enumerate(data):
        options.append(
            f'{base_index + index} - {market["creatorName"]}: {market["question"]}')
    options.append("Next page ->")
    _option, index = pick(options, "Select market you wish to view")
    if index == 0:
        choose_navigation()
    elif index == len(options) - 1:
        show_markets(data[index - 2]["id"], base_index + index - 1)
    else:
        show_market_by_id(data[index - 1]["id"])


def show_market_by_url(market_url):
    data = get_market_data_by_url(market_url)
    show_market(data)


def show_market_by_id(market_id):
    data = get_market_data(market_id)
    show_market(data)


def show_market(data):
    options = ["Yes", "No"]
    index = 0
    _option, index = pick(
        options, wrap_string(f'Question: {data["question"]}\n\nDescription: {data["textDescription"]}\n\nCurrent probability: {format_probability(data["probability"])}\n\n - Do you want GPT-Manifold to make a prediction?'))
    if index == 0:
        prompt(market_id)
    else:
        choose_navigation()


def show_market_url_input():
    market_url = print_input("Enter the URL of the market you wish to view: ")
    show_market_by_url(market_url)


def prompt(market_id):
    data = get_market_data(market_id)
    title = data["question"]
    description = data["textDescription"]
    probability = format_probability(data["probability"])

    user_prompt = user_template.format(
        title=title, description=description, probability=probability, play_money=balance)
    system_prompt = system_template.format(max_bet=max_bet)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    answer = get_completion(messages)

    last_tag = find_tags(answer)[-1]
    action = last_tag[0]
    amount = re.sub("[^0-9]", "", last_tag[1])
    options = ["Yes", "No"]
    _option, index = pick(
        options, wrap_string(f'{answer}\n\nThe chosen action is {action} with a value of {amount}\nYour current balance is {balance}.\nDo you want to execute that action?'))
    if index == 0:
        if (action == "ABSTAIN"):
            choose_navigation()
        else:
            place_bet(market_id, action, amount, answer)
    else:
        choose_navigation()


def place_bet(market_id, bet_outcome, bet_amount, comment):
    post_bet(market_id, bet_amount, bet_outcome)
    options = ["Yes", "No"]
    _option, index = pick(
        options, wrap_string("Bet successfully placed! Would you like to post GPT-Manifold's reasoning as a comment? Please don't spam the markets!"))
    next_pick = ""
    if index == 0:
        next_pick = "Comment successfully posted!"
        post_comment(market_id, comment)
    _option, index = pick(
        options, wrap_string(f'{next_pick} Would you like to view other markets?'))
    if index == 0:
        choose_navigation()
    else:
        exit()


def find_tags(text):
    tag_pattern = re.compile(r'<(\w+)[^>]*>(.*?)<\/\1>|<(\w+)\/>')
    matches = tag_pattern.findall(text)
    parsed_tags = []
    for match in matches:
        if match[0]:
            tag_name = match[0]
            content = match[1]
        else:
            tag_name = match[2]
            content = "0"
        parsed_tags.append((tag_name, content))
    if len(parsed_tags) == 0:
        parsed_tags.append("ABSTAIN", "0")
    return parsed_tags


def format_probability(probability):
    return f'{round(probability * 100, 2)}%'


def wrap_string(text):
    output = ""
    for paragraph in text.split("\n"):
        output += textwrap.fill(paragraph, width=80) + "\n"
    return output


def print_status(text):
    cls()
    print(text)


def print_input(text):
    cls()
    return input(text)


def cls():
    os.system('cls' if os.name == 'nt' else 'clear')


if __name__ == '__main__':
    init()
