import socket

TARGET_IP = "127.0.0.1"
PORT = 5001

pending_messages = {}  # {id_inteiro: "texto da mensagem"}
msg_counter = 1


def drain_receipts(s):
  """
  Verifica, de forma NÃO bloqueante, se chegaram recibos DELIVERED
  e atualiza pending_messages. Substitui a thread de escuta: em vez de
  ficar bloqueado esperando, tentamos ler e, se não tiver nada, seguimos
  em frente imediatamente (BlockingIOError / timeout).
  """
  s.settimeout(0)  # modo não-bloqueante
  while True:
    try:
      data, _ = s.recvfrom(1024)
      raw = data.decode("utf-8")
      parts = raw.split("|")
      if len(parts) == 2 and parts[0] == "DELIVERED":
        msg_id = int(parts[1])
        if msg_id in pending_messages:
          texto = pending_messages.pop(msg_id)
          print(f"[✓✓ Entregue] ID {msg_id}: {texto}")
    except (BlockingIOError, socket.timeout):
      break
    except Exception:
      break
  s.settimeout(None)  # volta ao modo bloqueante normal para o resto do código


def run_chat_sender():
  global msg_counter

  with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    print("=== Mini-Chat UDP (versão sem threading) ===")
    print("Comandos especiais:")
    print("  /status   -> Mostra mensagens ainda pendentes")
    print("  /reenviar -> Reenvia todas as mensagens pendentes\n")

    while True:
      try:
        # Antes de cada novo comando, drena os recibos que chegaram
        # enquanto o usuário estava digitando.
        drain_receipts(s)

        user_input = input("Digite uma mensagem: ").strip()
        if not user_input:
          continue

        # Drena de novo logo após o Enter, para status/reenviar já saírem atualizados
        drain_receipts(s)

        if user_input == "/status":
          if pending_messages:
            print(f"[STATUS] {len(pending_messages)} mensagem(ns) pendente(s):")
            for mid, texto in pending_messages.items():
              print(f"  ID {mid}: {texto}")
          else:
            print("[STATUS] Nenhuma mensagem pendente. Tudo entregue!")
          continue

        if user_input == "/reenviar":
          if not pending_messages:
            print("[REENVIAR] Nenhuma mensagem pendente para reenviar.")
          else:
            for mid, texto in pending_messages.items():
              packet = f"MSG|{mid}|{texto}"
              s.sendto(packet.encode("utf-8"), (TARGET_IP, PORT))
              print(f"[REENVIADO] ID {mid}: {texto}")
          continue

        # Envio de mensagem normal
        current_id = msg_counter
        pending_messages[current_id] = user_input
        msg_counter += 1

        packet = f"MSG|{current_id}|{user_input}"
        s.sendto(packet.encode("utf-8"), (TARGET_IP, PORT))
        print(f"[PENDENTE] Mensagem ID {current_id} enviada. Aguardando confirmação...")

      except KeyboardInterrupt:
        print("\nEncerrando cliente...")
        break


if __name__ == "__main__":
  run_chat_sender()
