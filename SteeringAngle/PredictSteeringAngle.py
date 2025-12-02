import cv2
import tensorflow as tf
import numpy as np
import os

# Get directory of the current script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to the trained .h5 model
model_path = os.path.join(BASE_DIR, "model_final.h5")

# Load the model for inference only (ignore Lambda, metrics, loss issues)
model = tf.keras.models.load_model(model_path, safe_mode=False, compile=False)
print(f"Loaded model from: {model_path}")

# Capture from webcam
cap = cv2.VideoCapture(0)  # 0 = default webcam

def preprocess_image(img):
    """Preprocess frame same as during training"""
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (200, 66))  # NVIDIA model input
    img = img.astype(np.float32) / 255.0 - 0.5
    return img

print("Starting webcam feed. Press 'q' to quit.")
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Preprocess and add batch dimension
    processed = np.expand_dims(preprocess_image(frame), axis=0)

    # Predict steering angle
    steering_angle = float(model.predict(processed, verbose=0))
    print("Predicted Steering:", steering_angle)

    # Show webcam feed
    cv2.imshow("Webcam Feed", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
