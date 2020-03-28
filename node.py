import block
import wallet
from blockchain import BlockChain
import settings
import threading
from collections import deque
from copy import deepcopy
from random import randint
from miner import Miner
from blockchain_subjects import minerS

class node:
    def __init__(self, id, ip, port, wallet):

        self.id = int(id)
        self.wallet = wallet
        self.ip = ip
        self.port = port
        self.chain = BlockChain()
        self.lock = threading.Lock()
        self.current_block = []		# TODO: Imporve this
        self.miner = Miner()
        # here we store information for every node, as its id, its (ip:port) its public key and its UTXOS (sender address: receiver id, amount)
        self.ring = []
        self.current_node_count = len(self.ring)

    def hier_miner(self):
        self.miner = Miner()

    def get_suffisient_UTXOS(self, ammount):
        UTXOS = self.get_node_UTXOS(self.id)
        t_ids = []
        balance = 0
        for id in UTXOS:
            if balance >= ammount:
                break
            balance += UTXOS[id][1]
            t_ids.append(id)
        return t_ids, balance

    def get_node_UTXOS(self, id):
        _, _, _, utxos = self.ring[id]
        return utxos

    def get_all_UTXOS(self):
        return [utxos for _, _, _, utxos in self.ring]

    def set_all_utxos(self, UTXOS):
        self.ring = [(ring_entry[0], ring_entry[1], ring_entry[2], deepcopy(UTXO))
                     for ring_entry, UTXO in zip(self.ring, UTXOS)]

    def get_node_balance(self, id):
        UTXOS = self.get_node_UTXOS(id)
        return sum([amount for _, amount in UTXOS.values()])

    def set_ring(self, ring):
        self.ring = ring

    def get_pending_transactions(self):
        return [t.transaction_id for t in self.current_block]

    def get_hosts(self):
        return [(ip, port) for ip, port, _, _ in self.ring]

    def get_other_hosts(self):
        return [(ip, port) for ind, (ip, port, _, _) in enumerate(self.ring) if ind != self.id]

    def address_to_host(self, address):
        match = [(ip, port)
                 for ip, port, pkey, _ in self.ring if pkey == address]
        if len(match) > 0:
            return match[0]
        return 0

    def address_to_id(self, address):
        match = [id for id, (_, _, pkey, _) in enumerate(
            self.ring) if pkey == address]
        return match[0]

    # def create_new_block():

    # def create_transaction(sender, receiver, signature):
    # 	#remember to broadcast it

    # def broadcast_transaction():

    def validate_transaction(self, t, UTXOS, verbose=False):
        current_balance = 0
        if(t.receiver_address == t.sender_address):
            if verbose:
                print('Cannot send transaction to self')
            return None

        UTXOS_sender = UTXOS[
            self.address_to_id(t.sender_address)]
        UTXOS_receiver = UTXOS[
            self.address_to_id(t.receiver_address)]

        for id in t.transaction_inputs:
            if id in UTXOS_sender:
                current_balance += UTXOS_sender[id][1]
            else:
                if verbose:
                    print('Input not found')
                return None

        if current_balance < t.amount:
            if verbose:
                print('Amount not found')
            return None

        for id in t.transaction_inputs:
            del UTXOS_sender[id]

        UTXOS_sender[t.transaction_id] = (
            t.sender_address, t.transaction_outputs[1]['amount'])
        UTXOS_receiver[t.transaction_id] = (
            t.receiver_address, t.transaction_outputs[0]['amount'])

        return UTXOS

    def validate_transactions(self, ts, initial_utxos):
        temp_utxos = deepcopy(initial_utxos)
        valid_transactions = []

        for t in ts:
            new_utxos = self.validate_transaction(t, temp_utxos)
            if new_utxos != None:
                valid_transactions.append(t)
                temp_utxos = new_utxos

        return valid_transactions, temp_utxos

    def validate_block(self, new_block, UTXOS):
        valid_transactions, new_utxos = self.validate_transactions(new_block.transactions, UTXOS)
        success = len(valid_transactions) == len(new_block.transactions)

        # if all transactions of the block are valid => update utxos
        # else failure

        if success:
            return new_utxos
        else:
            return None

    def clear_current_block(self):
        # we clear our local current block (validated transaction pool)
        # based on the new blockchain, we keep only valid transactions in our current block and update our utxos accordingly

        valid_transactions, new_utxos = self.validate_transactions(self.current_block, self.chain.get_recent_UTXOS())
        self.current_block = valid_transactions
        self.set_all_utxos(new_utxos)

    def add_transaction_to_block(self, t):
        self.current_block.append(t)
        if len(self.current_block) >= settings.capacity:
            minerS.on_next(0)

    def look_for_ore_block(self):
        index = self.chain.get_last_block().index+1
        hs = self.chain.get_last_block().current_hash
        b = block.Block(index, hs, 0)
        b.transactions = self.current_block[:settings.capacity]
        return b

    def verify_chain(self, blocks, index):
        print('verification at block index: {}'.format(blocks[0].index))
        
        temp_blocks = [self.chain.chain[index - 1]] + blocks

        for i in range(len(temp_blocks) - 1):
            if not(temp_blocks[i + 1].verify_block(temp_blocks[i], True)):
                return False

        return True

    def validate_chain(self, blocks, index):
        max_common_index = self.chain.get_max_prefex_block_chain(blocks, index)

        temp_UTXOS = [self.chain.UTXO_history[index+max_common_index-1]]
        transactions = set()

        for block in blocks[max_common_index:]:
            new_UTXOS = self.validate_block(block, temp_UTXOS[-1])
            if new_UTXOS == None:
                return None
                
            transactions.update([t.transaction_id for t in block.transactions])
            temp_UTXOS.append(new_UTXOS)

        return temp_UTXOS[1:], index + max_common_index, transactions

    # def broadcast_block():

    # def valid_proof(.., difficulty=MINING_DIFFICULTY):

    # #concencus functions

    # def valid_chain(self, chain):
    # 	#check for the longer chain accroose all nodes
    # def resolve_conflicts(self):
    # 	#resolve correct chain
