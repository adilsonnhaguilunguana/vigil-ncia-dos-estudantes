import cv2
#Troca pelo IP que aparece no teu celular!
IP_CELULAR = "10.40.89.170:8080"

url = f"http://{IP_CELULAR}/video"

camera = cv2.VideoCapture(url)

# Cria a janela com nome
cv2.namedWindow("Camera Celular", cv2.WINDOW_NORMAL)

# Define o tamanho (largura x altura)
cv2.resizeWindow("Camera Celular", 800, 600)

while True:
    ret, frame = camera.read()

    if not ret:
        break

    cv2.putText(frame, "Adilson", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.imshow("Camera Celular", frame)

    if cv2.waitKey(1) == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()