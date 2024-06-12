import socket
import time
import zlib
import random
import hashlib
import sys

# Configuracao do servidor
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5555

BUFFER_SIZE = 1024
TIMEOUT = 2  # Timeout para esperar ACKs
SLOW_START_THRESHOLD = 16  # Threshold para transicao de slow start para congestion avoidance


# Calcula o hash MD5 dos dados
def calculate_md5(data):
    md5 = hashlib.md5()
    md5.update(data)
    return md5.hexdigest()

# Calcula o checksum CRC32 dos dados
def calculate_crc(data):
    return zlib.crc32(data)

def send_file(filename, server_address):
    # Cria um socket UDP
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(TIMEOUT)
    
    # Lê o conteúdo do arquivo
    with open(filename, 'rb') as f:
        file_data = f.read()
    
    # Divide o arquivo em pacotes de 10 bytes
    file_size = len(file_data)
    num_packets = file_size // 10 + (1 if file_size % 10 != 0 else 0)
    
    # Dados iniciais do envio
    seq_num = 0
    expected_ack = 0
    congestion_window = 1
    ssthresh = SLOW_START_THRESHOLD

    # Estabelecendo conexão com o servidor
    print("Estabelecendo conexão...")
    client_socket.sendto(b'CONNECT', server_address)
    try:
        ack_packet, _ = client_socket.recvfrom(BUFFER_SIZE)
        if ack_packet == b'ACK':
            print("Conexão estabelecida com servidor.")
        else:
            print("Falha ao estabelecer conexão. Encerrando envio.")
            return
    except socket.timeout:
        print("Timeout ao aguardar ACK de conexão. Encerrando envio.")
        return

    # Envio dos pacotes
    print(f"\nEnviando arquivo '{filename}' com {num_packets} pacotes...\n")
    while expected_ack < num_packets:
        # Envia o numero de pacotes dentro da janela
        for i in range(congestion_window):
            if seq_num >= num_packets:
                break
            
            start = seq_num * 10
            end = start + 10
            data = file_data[start:end].ljust(10, b'\x00')
            crc = calculate_crc(data)

            # Introduz erro de CRC aleatoriamente
            if random.randint(1, 10) < 2:
               crc = 0

            packet = str(seq_num).zfill(4).encode() + str(crc).zfill(10).encode() + data

            client_socket.sendto(packet, server_address)
            print(f"Enviado pacote {seq_num} com CRC {crc}.")
            seq_num += 1

        try:
            ack_packet, _ = client_socket.recvfrom(BUFFER_SIZE)
            ack_str = ack_packet.decode()

            if ack_str.startswith("ACK"):
                ack_num = int(ack_str[3:])
                print(f"ACK {ack_num} recebido.")

                if ack_num >= expected_ack:
                    expected_ack = ack_num + 1

                # Fica em Slow Start, duplica tamanho da janela 
                if congestion_window < ssthresh:
                    congestion_window *= 2  # Slow Start
                    print(f"Slow Start: congestion window = {congestion_window}")
                else:
                # Troca para Congestion Avoidance, tamanho da janela + 1  
                    congestion_window += 1  # Congestion Avoidance
                    print(f"Congestion Avoidance: congestion window = {congestion_window}")

                # Sai do loop se receber um ACK para o próximo pacote inexistente
                if ack_num >= num_packets:
                    break  

        except socket.timeout:
            # Em caso de timeout, reinicia o Slow Start
            print(f"---- Timeout. Reiniciando Slow Start. ----")
            seq_num = expected_ack
            congestion_window = 1 # volta tamanho da janela para 1
    
    # Envia o hash MD5 junto com o último pacote
    file_md5 = calculate_md5(file_data)
    md5_packet = b'MD5' + file_md5.encode()
    print(f"\nMD5 calculado do arquivo enviado: {file_md5}")

    time.sleep(2)

    client_socket.sendto(md5_packet, server_address)
    print("\nEnvio do arquivo concluído.")
    client_socket.close()
    
if __name__ == "__main__":
    filename = sys.argv[1]
    server_address = (SERVER_HOST, SERVER_PORT)
    send_file(filename, server_address)
