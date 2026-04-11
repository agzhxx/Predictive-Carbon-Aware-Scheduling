import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import os
import joblib
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import DataLoader, TensorDataset

class LSTMForecaster(nn.Module):
    def __init__(self, input_size=1, hidden_layer_size=50, output_size=1):
        super(LSTMForecaster, self).__init__()
        self.hidden_layer_size = hidden_layer_size
        self.lstm = nn.LSTM(input_size, hidden_layer_size, batch_first=True)
        self.linear = nn.Linear(hidden_layer_size, output_size)

    def forward(self, input_seq):
        lstm_out, _ = self.lstm(input_seq)
        predictions = self.linear(lstm_out[:, -1, :])
        return predictions

class CarbonIntensityModel:
    def __init__(self, use_lstm=True, sequence_length=24):
        self.use_lstm = use_lstm
        self.sequence_length = sequence_length
        self.scaler = MinMaxScaler(feature_range=(-1, 1))
        self.model = None

    def train(self, data: pd.Series, epochs=50, lr=0.001):
        """
        Trains the forecasting model on historical carbon intensity values.
        `data` should be a pandas Series of hourly carbon intensities.
        """
        if not self.use_lstm:
            print("Using naive Moving Average, no training required.")
            return

        values = data.values.reshape(-1, 1)
        scaled_data = self.scaler.fit_transform(values)

        X, y = [], []
        for i in range(len(scaled_data) - self.sequence_length):
            X.append(scaled_data[i:i+self.sequence_length])
            y.append(scaled_data[i+self.sequence_length])

        X = torch.FloatTensor(np.array(X))
        y = torch.FloatTensor(np.array(y))

        dataset = TensorDataset(X, y)
        loader = DataLoader(dataset, batch_size=32, shuffle=True)

        self.model = LSTMForecaster()
        loss_fn = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        print("Training LSTM Forecaster (with Early Stopping)...")
        best_loss = float('inf')
        patience = 5
        trigger_times = 0
        best_model_state = None

        for epoch in range(epochs):
            total_loss = 0
            self.model.train()
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                y_pred = self.model(batch_X)
                loss = loss_fn(y_pred, batch_y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            avg_loss = total_loss / len(loader)
            
            # Early Stopping logic
            if avg_loss < best_loss:
                best_loss = avg_loss
                trigger_times = 0
                best_model_state = self.model.state_dict()
            else:
                trigger_times += 1
                if trigger_times >= patience:
                    print(f"Early stopping triggered at epoch {epoch}. Best Loss: {best_loss:.4f}")
                    self.model.load_state_dict(best_model_state)
                    break

            if epoch % 10 == 0:
                print(f"Epoch {epoch} Avg Loss: {avg_loss:.4f}")

    def predict_multi(self, recent_history: list, steps: int = 1) -> float:
        """
        Predicts the carbon intensity 'steps' hours into the future using recursive forecasting.
        """
        if not self.use_lstm:
            return float(np.mean(recent_history[-self.sequence_length:]))

        if self.model is None:
            raise ValueError("Model is not trained. Call train() first.")

        # Copy history so we don't mutate input
        hist = list(recent_history[-self.sequence_length:])
        if len(hist) < self.sequence_length:
            hist = [hist[0]] * (self.sequence_length - len(hist)) + hist

        self.model.eval()
        last_pred = 0
        
        with torch.no_grad():
            for _ in range(steps):
                scaled_hist = self.scaler.transform(np.array(hist[-self.sequence_length:]).reshape(-1, 1))
                x_tensor = torch.FloatTensor(scaled_hist).unsqueeze(0)
                pred_scaled = self.model(x_tensor).item()
                last_pred = self.scaler.inverse_transform([[pred_scaled]])[0][0]
                # Feed prediction back into history for recursive step
                hist.append(last_pred)
                
        return float(last_pred)

    def save_model(self, base_path: str):
        """Saves the PyTorch model state and the data scaler."""
        if not self.use_lstm or self.model is None:
            return
        os.makedirs(os.path.dirname(base_path), exist_ok=True)
        torch.save(self.model.state_dict(), f"{base_path}.pth")
        joblib.dump(self.scaler, f"{base_path}_scaler.pkl")

    def load_model(self, base_path: str) -> bool:
        """Loads the PyTorch model state and data scaler. Returns True if successful."""
        if not self.use_lstm:
            return False
            
        if os.path.exists(f"{base_path}.pth") and os.path.exists(f"{base_path}_scaler.pkl"):
            self.model = LSTMForecaster()
            self.model.load_state_dict(torch.load(f"{base_path}.pth"))
            self.model.eval()
            self.scaler = joblib.load(f"{base_path}_scaler.pkl")
            return True
        return False

    def predict(self, recent_history: list) -> float:
        """
        Predicts the next hour's carbon intensity based on recent history.
        """
        if not self.use_lstm:
            # Baseline: Simple moving average of the last few hours
            return float(np.mean(recent_history[-self.sequence_length:]))

        if self.model is None:
            raise ValueError("Model is not trained. Call train() first.")

        # Ensure we have enough history
        hist = recent_history[-self.sequence_length:]
        if len(hist) < self.sequence_length:
            # Pad with the earliest available value
            hist = [hist[0]] * (self.sequence_length - len(hist)) + hist

        scaled_hist = self.scaler.transform(np.array(hist).reshape(-1, 1))
        x_tensor = torch.FloatTensor(scaled_hist).unsqueeze(0)

        self.model.eval()
        with torch.no_grad():
            pred_scaled = self.model(x_tensor).item()
        
        pred_unscaled = self.scaler.inverse_transform([[pred_scaled]])[0][0]
        return float(pred_unscaled)

if __name__ == "__main__":
    # Test with dummy data
    timeseries = pd.Series(np.sin(np.linspace(0, 100, 1000)) * 100 + 300)
    model = CarbonIntensityModel(use_lstm=True, sequence_length=24)
    model.train(timeseries, epochs=20)
    pred = model.predict(timeseries.tolist()[-24:])
    print(f"Predicted next value: {pred:.2f}")

