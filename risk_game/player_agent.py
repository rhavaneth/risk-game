import json
import re
from typing import Dict,Optional,List,Tuple
from network_utils import GroqClient

class PlayerAgent:
    def __init__(self, name: str, model_number: int)-> None:
        self.name: str = name
        self.model_number: int = model_number
        self.agent_model = GroqClient(model_number)
        self.include_reasoning: bool = True
        self.troops: int = 0
    
    def _send_message(self, message_content: str) -> str:
        messages = [
            {
                "role": "user",
                "content": message_content
            }
        ]
        return self.agent_model.get_chat_completion(messages)

    def parse_response_text(
        self, move_response: object
    ) -> Tuple[List[Dict[str, int]], Optional[str], Optional[str]]:
        response = move_response.choices[0].message.content
        # print(f"Response content: {response}")

        # Regular expression to extract all moves (e.g., |||Territory, 3|||)
        move_matches = re.findall(r'\|\|\|\s*(.+?)\s*,\s*(\d+)\s*\|\|\|', response)
        reasoning_match = re.search(r'\+\+\+\s*(.+?)\s*\+\+\+', response)
        from_territory_match = re.search(r'\#\#\#\s*(.+?)\s*\#\#\#', response)

        moves = []
        reasoning = None
        from_territory = None

        print(f"move_matches: {move_matches}")  # Debugging print
        # print(f"reasoning_match: {reasoning_match}")  # Debugging print
        # print(f"from_territory_match: {from_territory_match}")  # Debugging print

        if move_matches:
            for match in move_matches:
                territory_name = match[0].strip()
                num_troops = int(match[1].strip())
                moves.append({
                    'territory_name': territory_name,
                    'num_troops': num_troops
                })

            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()

            if from_territory_match:
                from_territory = from_territory_match.group(1).strip()

            return moves, reasoning, from_territory
        else:
            print(f'''------__------Error parsing response: ------__------
                  {response}''')
            return [{'territory_name': None, 'num_troops': None}], None, None

        
    def make_initial_troop_placement(
            self, game_state: 'GameState') -> str:
        # Implement strategy to make a move
        game_state_json = game_state.territories_df.to_json()
        player_territories = game_state.get_player_territories(self.name)
        prompt = f"""
        We are playing Risk and we are in the troop placement phase.
        The current game state is {game_state_json}. 
        You, are {self.name}, and you control the following territories: 
        {player_territories}. From the list of territories you control, and
        only from the list of territories you control, please suggest a 
        move. You can only place one troop. Think carefully
        about your move and consider also the moves of other players. 

        Your response should be in the following format:
        Move:|||Territory, Number of troops|||
        Reasoning:+++Reasoning for move+++

        For example:
        Move:|||Brazil, 1|||
        Reasoning:+++Brazil is a key territory in South America.+++

        Only provide the response in the specified format and please keep your 
        reasoning very brief. And you must remebmer to choose a territory 
        you control, this is very important for the grading of your submission.
        """
        parsed_response = (
            self.parse_response_text(
                self._send_message(
                 prompt))
        )
        return parsed_response
    

    def make_troop_placement(
            self, game_state: 'GameState') -> str:
        game_state_json = game_state.territories_df.to_json()
        player_territories = game_state.get_player_territories(self.name)

        prompt = f"""
        We are playing Risk and it is your turn. This is the troop placement 
        phase. The current game state is {game_state_json}. 
        You, are {self.name}, and you control the following territories: 
        {player_territories}. From the list of territories you control, and
        only from the list of territories you control, please suggest your moves.
        You can place troops on any of the territories you control,
        and you must place the number of available troops. 
        You have {self.troops} to place. Think carefully
        about your move and consider also the moves of other players. 

        Your response should be in the following format:

        Move 1: |||Territory, Number of troops|||

        Move 2: |||Territory, Number of troops|||

        Move 3: |||Territory, Number of troops|||

        For as many moves as you need to place all your troops.

        Reasoning:+++Reasoning for move+++

        For example:

        Move 1: |||Brazil, 1|||

        Move 2: |||Argentina, 2|||

        Move 3: |||Peru, 4|||

        Reasoning: +++Brazil, Argentina and Peru are key in South America+++

        Only provide the response in the specified format and please keep your 
        reasoning very brief. And remember you must choose territories you
        control, this is very important for the grading of your submission!
        """
        parsed_response = (
            self.parse_response_text(
                self._send_message(
                 prompt))
        )

        return parsed_response
    
    def make_fortify_move(
            self, game_state: 'GameState') -> str:
        # Implement strategy to make a move
        game_state_json = game_state.territories_df.to_json()
        strong_territories = game_state.get_strong_territories(self.name)
        territories_with_troops  = (
            game_state.get_strong_territories_with_troops(self.name))


        prompt = f"""
        We are playing Risk and we are in the troop fortify phase.
        The current game state is {game_state_json} and you are {self.name}.
        To choose a territory to fortify from, you need to have more than one 
        troop in that territory. 
        The territories you have more than one troop in are: {strong_territories}.
        Remember, to fortify is optional and you can choose not to fortify.

        If you choose to fortify, choose a territory ONLY from the following
        list of tuples containing territories and troop numbers:
        {territories_with_troops}. The troop number indicates the maximum
        numer of troops you can move from that territory.

        Also, most importantly, you MUST fortify between two territories 
        that are connected by a chain of territories under your control.

        To Territory:|||To Territory, Number of troops|||
        From Territory: ### From Territory ###
        Reasoning:+++Reasoning for move+++

        For example:
        To Territory:|||Brazil, 1|||
        From Territory:###Argentina###

        Reasoning:+++I need more troops in Brazil+++

        If you don't want to fortify, you can provide the following response:
        To Territory:|||Blank, 0|||
        From Territory:###Blank###
        Reasoning:+++I don't want to fortify+++

        Only provide the response in the specified format and please keep your 
        reasoning brief, this is very important for the grading of your 
        submission.
        """
        parsed_response = (
            self.parse_response_text(
                self._send_message(
                 prompt))
        )

        return parsed_response

    def make_attack_move(
            self, game_state: 'GameState', successful_attacks: int) -> str:
        # Implement strategy to make an attack
        game_state_json = game_state.territories_df.to_json()
        strong_territories = game_state.get_strong_territories(self.name)
        territories_with_troops  = (
            game_state.get_strong_territories_with_troops(self.name))
        
        possible_attach_vectors = (
            game_state.get_adjacent_enemy_territories(
                self.name, territories_with_troops))

        prompt = f"""
        We are playing Risk and we are in the attack phase.     
        The current game state is {game_state_json} and you are {self.name}.
        You have had {successful_attacks} successful attacks so far. 

        You can only attack FROM the following territories: {strong_territories}.

        The maximum number of troops you can attack with is given by the 
        following list of tuples containing territories and troop numbers:
        {territories_with_troops}.

        The following dictionary contains the territories you can attack FROM, 
        the maximum number of troops you can attack with and the possible
        territories you can attack from those territories 
        {possible_attach_vectors}. Your attack MUST be chosen using one of the 
        options in this dictionary. (you can chose to attack with less troops 
        than the maximum number of troops in the dictionary).

        PRO TIP: When attacking, it is always a good idea to attack with 3 or 
        more troops, because you will have a higher chance of winning the 
        attack. This is because the defender always wins if the dice rolls are 
        equal.

        Remember, to attack is optional and you can choose not to attack. 
        however, if you don't have any successful attacks, you will not 
        receive a card.

        Your response MUST be in the following format:

        Attack Opponent Territory:||| Territory, Number of troops|||
        From Territory: ### From Territory ###
        Reasoning:+++Reasoning for move+++

        For example:
        Attack Opponent Territory:|||Brazil, 3|||
        From Territory:###Argentina###

        Reasoning:+++I want to attack Brazil with 3 troops from Argentina because it will help give me control over South America+++

        If you are finished attacking, or don't want to attack this turn,
        you can provide the following response:
        
        Attack Opponent Territory:|||Blank, 0|||
        From Territory:###Blank###
        Reasoning:+++I am finished attacking because I don't want to overextend+++

        Only provide the response in the specified format and please keep your 
        reasoning brief, this is very important for the grading of your 
        submission.
        """
        parsed_response = (
            self.parse_response_text(
                self._send_message(
                 prompt))
        )

        return parsed_response

    
    def propose_trade(self, game_state: 'GameState') -> List[str]:
        f"""
        You are playing Risk and are currently in the card trade phase. 
        The following is a list of cards you have:

        Ural Infantry
        Afghanistan Cavalry
        Ontario Infantry
        Peru Infantry
        
        Instructions:
        
        Objective: Your goal is to decide whether to trade in a set of three 
        cards or to hold onto your cards for future turns.
        
        Rules:
        
        Valid Sets:
        
        Three of a Kind: Three cards of the same type (e.g., three Infantry cards).
        
        One of Each Type: One Infantry, one Cavalry, and one Artillery card.
        
        Wild Cards (if available) can substitute for any type of card.
        
        Strategy Considerations:
        
        Maximize Troop Gain: Trading in a set of cards will provide you with 
        additional troops. Consider whether the trade will significantly 
        strengthen your position.
        
        Hold for Later: Sometimes it may be better to hold onto your cards to 
        create a stronger set in future turns, especially if you are not in 
        immediate need of additional troops.
        
        Opponent Awareness: Consider the state of your opponents. If they are weak or you have a strategic advantage, it might be worth trading in cards to press your advantage. Conversely, if you are in a strong position, holding cards for later might be more beneficial.
        
        
        Response Format:
        
        If you decide to trade in a set of cards, respond with the list of 
        card numbers in the format:
        
        List of cards to trade ||| [Card Numbers] |||

        Example:
        List of cards to trade ||| 1, 3, 4 |||

        If you decide not to trade any cards, respond with:
        ||| 0 |||

        Example Scenario:
        Based on the cards provided:

        Ural Infantry
        Afghanistan Cavalry
        Ontario Infantry
        Peru Infantry
        
        You could potentially trade the three Infantry cards 
        (cards 1, 3, and 4). However, if you believe that holding onto the 
        cards will benefit you more in the long run, you can choose not to trade.

        """
        
        pass

    def agree_to_trade(self, game_state: 'GameState') -> bool:
        # Implement strategy to agree to a trade
        # return True if the player agrees to the trade, False otherwise
        pass
    
    def choose_capital(self, game_state: 'GameState') -> str:
        # Implement strategy to choose a capital
        # return the name of the capital
        pass

