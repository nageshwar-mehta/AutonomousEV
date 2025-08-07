import streamlit as st
import numpy as np
import time

# App title
st.title("⚡ Real-Time Graph Streaming")

# Chart placeholder
graph = st.line_chart([])

# Simulated data stream (replace this with your sensor/CAN data stream)
data = []

# Stream for 100 seconds
for i in range(100):
    new_point = np.sin(i * 0.1) + np.random.normal(0, 0.1)  # Simulated noisy sine wave
    data.append(new_point)

    # Keep last 50 points
    if len(data) > 50:
        data = data[-50:]

    # Update graph
    graph.line_chart(data)

    time.sleep(0.1)  # Simulate delay between data points
