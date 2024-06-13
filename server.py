import socket
import zlib
import time
import hashlib

# Configuracao do servidor
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5555

BUFFER_SIZE = 1024
TIMEOUT = 2  # Timeout para esperar ACKs

# Calcula o hash MD5 dos dados recebidos
def calculate_md5(data):
    md5 = hashlib.md5()
    md5.update(data)
    return md5.hexdigest()

# Calcula o checksum CRC32 dos dados recebidos
def calculate_crc(data):
    return zlib.crc32(data)

# Salva os dados recebidos em um novo arquivo
def save_file(file_data, filename):
    with open(filename, 'wb') as f:
        f.write(file_data)

def main():
    # Cria um socket UDP e vincula ao endereço e porta especificados
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    print(f"Servidor escutando em {SERVER_HOST}:{SERVER_PORT}")
    
    expected_seq_num = 0
    received_data = []

    print("Esperando mensagem de conexão...")
    # Aguarda a mensagem de conexão do cliente
    conn_packet, client_address = server_socket.recvfrom(BUFFER_SIZE)
    if conn_packet == b'CONNECT':
        print("Conexão estabelecida com cliente.")
        ack_packet = b'ACK'
        # Envia um ACK para confirmar a conexão
        server_socket.sendto(ack_packet, client_address)
    else:
        print("Mensagem de conexão inválida. Encerrando conexão.")
        return

    # Depois da conexão estabelecida, define o timeout para envio de pacotes
    server_socket.settimeout(TIMEOUT)

    # Transferência de dados
    print("\nRecebendo pacotes...\n")
    while True:
        try:
            # Aguarda a recepção de pacotes do cliente
            packet, client_address = server_socket.recvfrom(BUFFER_SIZE)

            # Verifica se o pacote contém o hash MD5 do arquivo recebido
            if packet.startswith(b'MD5'):
                md5_received = packet[3:].decode()
                print(f"\nMD5 recebido: {md5_received}")
                # Calcula MD5 do arquivo recebido removendo os bytes nulos
                file_data = b''.join(received_data).rstrip(b'\x00')
                file_md5 = calculate_md5(file_data)
                print(f"MD5 calculado: {file_md5}")

                # Compara o MD5 recebido com o MD5 calculado
                if md5_received == file_md5:
                    print(f"{time.time()} Arquivo recebido corretamente. MD5 corresponde.")
                else:
                    print(f"{time.time()} Arquivo recebido incorreto. MD5 não corresponde.")
                break


            # Extrai o número de sequência, CRC e os dados do pacote
            seq_num, crc_received, data = int(packet[:4].decode()), int(packet[4:14].decode()), packet[14:]

            # Guarda os pacotes recebidos
            recieved_packets = []
            
            # Verifica o CRC dos dados
            if calculate_crc(data) != crc_received:
                print(f"Erro de CRC no pacote {seq_num}. Pacote Descartado.")
                time.sleep(1)
                continue
            else:
                recieved_packets.append(seq_num)


            print(recieved_packets)

            # Verifica se o número de sequência está correto
            
            
            if seq_num == expected_seq_num:
                print(f"Pacote {seq_num} recebido corretamente.")
                received_data.append(data)
                expected_seq_num += 1
            else:
                print(f"Pacote {seq_num} fora de ordem. Esperando pacote {expected_seq_num}.")
                expected_seq_num = recieved_packets.pop()
                
            # Envia um ACK para o cliente
            ack_packet = f"ACK{expected_seq_num}".encode()
            print(f"Enviando ACK {expected_seq_num}")

            time.sleep(1)

            server_socket.sendto(ack_packet, client_address)


        except socket.timeout:
            # Se ocorrer um timeout, retransmite o último ACK esperado
            print("Timeout ocorreu. Retransmitindo último ACK esperado.")
            print(f"Enviando ACK {expected_seq_num}")
            ack_packet = f"ACK{expected_seq_num}".encode()
            
            server_socket.sendto(ack_packet, client_address)

    # Salva os dados recebidos em um arquivo e encerra a conexão
    file_data = b''.join(received_data)
    save_file(file_data, 'received_file')
    print("\nArquivo recebido e salvo.")
    server_socket.close()

if __name__ == "__main__":
    main()
