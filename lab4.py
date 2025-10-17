import hashlib
import datetime
import queue
import time
import threading


class Block:
    def __init__(self, index, timestamp, data, previous_hash, creator, nonce=0):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.creator = creator
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.index}{self.timestamp}{self.data}{self.previous_hash}{self.creator}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty):
        self.nonce = 0
        while True:
            self.hash = self.calculate_hash()
            if self.hash.startswith('0' * difficulty):
                break
            self.nonce += 1
        return self.nonce


class Blockchain:
    def __init__(self, difficulty):
        self.chain = []
        self.difficulty = difficulty
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = Block(0, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                              "Genesis Block", "0", "System")
        self.chain.append(genesis_block)

    def add_block(self, data, creator):
        previous_block = self.chain[-1]
        new_block = Block(len(self.chain), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          data, previous_block.hash, creator)
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        return new_block

    def is_valid(self):
        if self.chain[0].index != 0 or self.chain[0].previous_hash != "0":
            return False

        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.index != previous.index + 1:
                return False
            if current.previous_hash != previous.hash:
                return False
            if current.hash != current.calculate_hash():
                return False
            if not current.hash.startswith('0' * self.difficulty):
                return False

        return True


class Node:
    def __init__(self, node_id, difficulty):
        self.node_id = node_id
        self.blockchain = Blockchain(difficulty)
        self.peers = []
        self.incoming_queue = queue.Queue()
        self.is_mining = False

    def add_peer(self, peer_node):
        self.peers.append(peer_node)

    def broadcast_block(self, block):
        for peer in self.peers:
            peer.incoming_queue.put(block)

    def receive_block(self, block):
        print(f"{self.node_id} получил блок #{block.index} от {block.creator}")

        # Если уже майним - останавливаемся и принимаем чужой блок
        if self.is_mining and block.index == len(self.blockchain.chain):
            print(f"  ⏹️  Останавливаем майнинг, принимаем чужой блок")
            self.is_mining = False

        # Проверка валидности блока
        if block.index != len(self.blockchain.chain):
            print(f"  → Отклонён: неверный индекс")
            return False

        if block.previous_hash != self.blockchain.chain[-1].hash:
            print(f"  → Отклонён: неверный previous_hash")
            return False

        if block.hash != block.calculate_hash():
            print(f"  → Отклонён: недействительный хэш")
            return False

        if not block.hash.startswith('0' * self.blockchain.difficulty):
            print(f"  → Отклонён: хеш не соответствует сложности")
            return False

        # Блок валиден - добавляем
        self.blockchain.chain.append(block)
        print(f"  ✅ Принят блок: '{block.data}' от {block.creator}")

        # Ретрансляция
        for peer in self.peers:
            peer.incoming_queue.put(block)
        return True

    def process_next_message(self):
        if not self.incoming_queue.empty():
            block = self.incoming_queue.get()
            self.receive_block(block)

    def create_and_broadcast_block(self, data):
        print(f"\n{self.node_id} начинает майнинг блока...")
        self.is_mining = True

        # Майним блок локально
        new_block = self.blockchain.add_block(data, self.node_id)

        # Проверяем, не был ли уже принят блок от другого узла
        if self.is_mining:
            print(f"✅ {self.node_id} добыл блок #{new_block.index}: nonce={new_block.nonce} hash={new_block.hash}")

            # Рассылаем добытый блок
            self.broadcast_block(new_block)

            # Отправляем себе для обработки
            self.incoming_queue.put(new_block)
        else:
            print(f"⏹️  {self.node_id}: майнинг остановлен, блок уже получен от другого узла")

        self.is_mining = False


def simulate_network_delivery(sender, receiver, block):
    time.sleep(0.1)
    receiver.incoming_queue.put(block)


# Шаг 5: Симуляция работы сети с PoW
print("=== ШАГ 5: СИМУЛЯЦИЯ РАБОТЫ СЕТИ С PoW ===")

# Создаем узлы
node1 = Node("Node_1", difficulty=3)
node2 = Node("Node_2", difficulty=3)
node3 = Node("Node_3", difficulty=3)

# Создаем сеть
nodes = [node1, node2, node3]
for i, node in enumerate(nodes):
    for j, peer in enumerate(nodes):
        if i != j:
            node.add_peer(peer)

print("\nГенезис-блок создан")

# Запускаем одновременный майнинг
print("\n--- Одновременный майнинг двумя узлами ---")


def mine_block(node, data):
    node.create_and_broadcast_block(data)


# Запускаем майнинг одновременно
thread1 = threading.Thread(target=mine_block, args=(node1, "Транзакция А"))
thread2 = threading.Thread(target=mine_block, args=(node2, "Транзакция B"))
thread1.start()
thread2.start()
thread1.join()
thread2.join()

# Обрабатываем сообщения
print("\n--- Обработка сети ---")
for _ in range(10):
    for node in nodes:
        node.process_next_message()
    time.sleep(0.1)

print("\n--- Итоговые цепочки ---")
for node in nodes:
    chain_data = [f"#{b.index} '{b.data}' от {b.creator}" for b in node.blockchain.chain]
    print(f"{node.node_id}: {chain_data}")

# Проверяем консенсус
print("\n--- Проверка консенсуса ---")
chain_lengths = [len(node.blockchain.chain) for node in nodes]
if len(set(chain_lengths)) == 1:
    print(f"✅ Все цепочки одинаковой длины: {chain_lengths[0]}")

    # Проверяем идентичность блоков
    all_same = True
    for i in range(chain_lengths[0]):
        block_data = [node.blockchain.chain[i].data for node in nodes]
        if len(set(block_data)) != 1:
            print(f"❌ Блок #{i} различается: {set(block_data)}")
            all_same = False
            break

    if all_same:
        print("✅ КОНСЕНСУС ДОСТИГНУТ!")
    else:
        print("❌ Консенсус не достигнут")
else:
    print(f"❌ Цепочки разной длины: {chain_lengths}")

# Шаг 6 остается без изменений
print("\n=== ШАГ 6: ПРОВЕРКА ЗАЩИТЫ ОТ ПОДДЕЛКИ ===")

test_bc = Blockchain(difficulty=3)
test_bc.add_block("Тестовая транзакция", "Test_Node")

print("\n1. Исходная цепочка:")
for block in test_bc.chain:
    print(f"   Блок #{block.index}: '{block.data}', хеш: {block.hash[:16]}...")

print("\n2. Изменяем данные в блоке #1...")
test_bc.chain[1].data = "Поддельная транзакция!"

print("3. Проверяем валидность после изменения:")
print(f"   Цепочка валидна: {test_bc.is_valid()}")

print("\n4. Пытаемся 'исправить' хеш без майнинга...")
test_bc.chain[1].hash = test_bc.chain[1].calculate_hash()
print(f"   Цепочка валидна: {test_bc.is_valid()}")

print("\n5. Пробуем перемайнить блок...")
start_time = time.time()
test_bc.chain[1].mine_block(3)
mining_time = time.time() - start_time
print(f"   Время перемайнинга: {mining_time:.2f} сек")
print(f"   Цепочка валидна: {test_bc.is_valid()}")