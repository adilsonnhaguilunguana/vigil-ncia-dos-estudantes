import cv2

# ⚠️ Troca pelo IP que aparece no teu celular!
IP_CELULAR = "10.40.89.170:8080"
url = f"http://{IP_CELULAR}/video"

print(f"Conectando ao celular: {url}")

camera = cv2.VideoCapture(url)

if not camera.isOpened():
    print("ERRO: Não conseguiu conectar ao celular!")
    print("Verifica se o IP está correto e se estás na mesma rede Wi-Fi")
else:
    print("✓ Conectado! Pressione Q para sair.")

while True:
    ret, frame = camera.read()

    if not ret:
        print("Sem sinal do celular...")
        break

    cv2.putText(frame, "SmartSchool Guard - OK", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.imshow("Camera Celular", frame)

    if cv2.waitKey(1) == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()
print("Câmera fechada.")