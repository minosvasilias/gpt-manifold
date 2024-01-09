"""
A bot that aids in placing bets on manifold.markets using OpenAI's GPT APIs.
"""

import datetime
import os
import random
import textwrap
import openai
import requests
import re
from pick import pick
from logger import LogSession
from strings import *

model = ""
manifold_key = ""
max_bet = 0
balance = 0
page_limit = 100
group_pool_size = 100


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
    options = ["Recent Markets", "Market Groups",
               "Market URL", "Autonomous Bet", "Exit"]
    _option, index = pick(options, "Select navigation mode:")
    if index == 0:
        show_markets()
    elif index == 1:
        show_groups()
    elif index == 2:
        show_market_url_input()
    elif index == 3:
        choose_auto_bet()
    elif index == 4:
        exit()


def choose_auto_bet():
    options = ["Yes, but ask me for confirmation before betting.", "Yes, bet automatically but don't post a comment.",
               "Yes, bet automatically and post a comment, too!", "No, take me back."]
    _option, index = pick(options, auto_bet_info.format(
        model=model, group_pool_size=group_pool_size))
    if index == 0:
        prompt_for_group(False, False)
    elif index == 1:
        prompt_for_group(True, False)
    elif index == 2:
        prompt_for_group(True, True)
    elif index == 3:
        choose_navigation()


def get_all_groups():
    update_balance()
    print_status("Retrieving groups...")
    url = f'https://api.manifold.markets/v0/groups'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        raise RuntimeError(
            f"Error: Unable to retrieve group data (status code: {response.status_code})")


def get_group_markets(group_id):
    print_status("Retrieving markets for group...")
    url = f'https://api.manifold.markets/v0/group/by-id/{group_id}/markets'
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
    url = f'https://api.manifold.markets/v0/markets?limit={page_limit}&before={before_id}'
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
        url = f'https://api.manifold.markets/v0/slug/{market_slug}'
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
    url = f'https://api.manifold.markets/v0/market/{market_id}'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        raise RuntimeError(
            f"Error: Unable to retrieve market data (status code: {response.status_code})")


def update_balance():
    print_status("Updating current balance...")
    url = f'https://api.manifold.markets/v0/me'
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
    url = f'https://api.manifold.markets/v0/bet'
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
    disclaimer_comment = disclaimer.format(model=model, comment=comment)

    url = f'https://api.manifold.markets/v0/comment'
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
    print_status(f"Getting answer from {model}...")
    response = openai.ChatCompletion.create(
        model=model,
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
        prompt_for_prediction(data["id"])
    else:
        choose_navigation()


def show_market_url_input():
    market_url = print_input("Enter the URL of the market you wish to view: ")
    show_market_by_url(market_url)


def prompt_for_prediction(market_id, auto_bet=False, auto_comment=False):
    global log_session
    data = get_market_data(market_id)
    title = data["question"]
    description = data["textDescription"]
    probability = format_probability(data["probability"])

    user_prompt = user_template.format(
        title=title, description=description, probability=probability, play_money=balance)
    date = datetime.datetime.now()
    system_prompt = system_template.format(
        character=get_character(), date=date, max_bet=max_bet)

    log_session.write_message('BET PROMPT', system_prompt)
    log_session.write_message('BET INFO', user_prompt)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    answer = get_completion(messages)
    log_session.write_message('PREDICTION', answer)

    last_tag = find_tags(answer)[-1]
    action = last_tag[0]
    amount = re.sub("[^0-9]", "", last_tag[1])
    if (auto_bet):
        bet_pick = execute_action(market_id, action, amount, auto_comment)
        if (auto_comment):
            place_comment(market_id, answer, bet_pick, True)
        else:
            log_session.end_session()
            exit()
    else:
        options = ["Yes", "No"]
        _option, index = pick(
            options, wrap_string(f'{title}\n\n{answer}\n\nThe chosen action is {action} with a value of {amount}\nYour current balance is {balance}.\nDo you want to execute that action?'))
        if index == 0:
            bet_pick = execute_action(market_id, action, amount)
            place_comment(market_id, answer, bet_pick)
        else:
            choose_navigation()


def execute_action(market_id, action, amount, auto_comment=False):
    if (action == "YES" or action == "NO"):
        place_bet(market_id, action, amount)
        return "Bet successfully placed! "
    return "No bet placed. "


def prompt_for_group(auto_bet=False, auto_comment=False):
    global log_session
    log_session = LogSession()
    log_session.start_session()

    data = get_all_groups()
    random_groups = random.sample(data, group_pool_size)
    group_list_string = ""
    for group in random_groups:
        if (group["totalContracts"] > 9):
            group_list_string += f'{group["name"]}\n'

    user_prompt = group_list_string
    date = datetime.datetime.now()
    system_prompt = system_template_groups.format(
        character=get_character(), date=date)
    log_session.write_message('GROUP PROMPT', system_prompt)
    log_session.write_message('GROUP LIST', group_list_string)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    answer = get_completion(messages)
    log_session.write_message('SELECTED GROUP', answer)

    for group in random_groups:
        if group["name"] in answer:
            prompt_for_market(group["id"], auto_bet, auto_comment)
            return
    raise RuntimeError(
        f"Error: {model} was unable to pick a valid group: {answer}")


def prompt_for_market(group_id, auto_bet=False, auto_comment=False):
    global log_session
    data = get_group_markets(group_id)
    random_markets = random.sample(data, min(100, len(data)))
    market_list_string = ""
    for market in random_markets:
        if (market["isResolved"] == False and "probability" in market):
            market_list_string += f'{market["question"]}\n'

    user_prompt = market_list_string
    date = datetime.datetime.now()
    system_prompt = system_template_markets.format(
        character=get_character(), date=date)
    log_session.write_message('MARKET PROMPT', system_prompt)
    log_session.write_message('MARKET LIST', market_list_string)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    answer = get_completion(messages)
    log_session.write_message('SELECTED MARKET', answer)
    for market in random_markets:
        if market["question"] in answer:
            prompt_for_prediction(market["id"], auto_bet, auto_comment)
            return
    raise RuntimeError(
        f"Error: {model} was unable to pick a valid market: {answer}")


def place_bet(market_id, bet_outcome, bet_amount):
    global log_session
    post_bet(market_id, bet_amount, bet_outcome)
    log_session.write_message(
        'BET', f'Bet placed: {market_id}\n\n{bet_outcome} - {bet_amount}')


def place_comment(market_id, comment, bet_pick, auto_comment=False):
    global log_session
    if (auto_comment):
        post_comment(market_id, comment)
        log_session.write_message(
            'COMMENT', f'Comment posted: {market_id}\n\n{comment}')
        log_session.end_session()
        exit()
    else:
        options = ["Yes", "No"]
        _option, index = pick(
            options, wrap_string(f"{bet_pick}Would you like to post GPT-Manifold's reasoning as a comment? Please don't spam the markets!"))
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


def get_character():
    if model == "gpt-4":
        return gpt_4_character
    elif model == "gpt-3.5-turbo":
        return chat_gpt_character


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
