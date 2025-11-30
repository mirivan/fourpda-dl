import logging

def confirmation_request(prompt: str = "", default: bool = None) -> bool:
    if default is True:
        prompt_suffix = " [Y/n]"
    elif default is False:
        prompt_suffix = " [y/N]"
    else:
        prompt_suffix = " [y/n]"

    full_prompt = f"{prompt}{prompt_suffix}: "

    while True:
        response = input(full_prompt).strip().lower()
        
        if not response and default is not None:
            return default

        if response in ['y', 'yes', 'д', 'да']:
            return True

        if response in ['n', 'no', 'н', 'нет']:
            return False

        logging.info("Пожалуйста, ответьте 'y' (yes/да) или 'n' (no/нет)")