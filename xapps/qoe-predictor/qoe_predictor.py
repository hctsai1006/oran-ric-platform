#!/usr/bin/env python3
"""
QoE Predictor xApp
Machine Learning based Quality of Experience prediction
Uses LSTM models for throughput forecasting
"""

import json
import time
import logging
import pickle
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from threading import Thread, Lock
from datetime import datetime, timedelta
from collections import deque

from ricxappframe.xapp_frame import RMRXapp, rmr
from ricxappframe.xapp_sdl import SDLWrapper
from mdclogpy import Logger
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
import pandas as pd

# Configure logging
logger = Logger(name="qoe_predictor_xapp")
logger.set_level(logging.INFO)

# RMR Message Types
QOE_PRED_REQ = 30000
QOE_PRED_RESP = 30002
MODEL_UPDATE_REQ = 30010
MODEL_UPDATE_RESP = 30011
RIC_INDICATION = 12050

@dataclass
class QoEPrediction:
    """QoE prediction result"""
    ue_id: str
    serving_cell: str
    neighbor_cells: List[str]
    prediction_horizon: int  # seconds
    serving_cell_qoe: float
    neighbor_cell_qoe: Dict[str, float]
    confidence: float
    timestamp: datetime

@dataclass
class UEHistory:
    """Historical data for UE"""
    ue_id: str
    cell_id: str
    throughput_history: deque  # Limited size queue
    rsrp_history: deque
    rsrq_history: deque
    cqi_history: deque
    handover_history: List[Tuple[datetime, str, str]]  # (time, from_cell, to_cell)

class QoEModel:
    """LSTM model for QoE prediction"""
    
    def __init__(self, sequence_length: int = 20, features: int = 4):
        self.sequence_length = sequence_length
        self.features = features
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def build_model(self):
        """Build LSTM model architecture"""
        model = Sequential([
            LSTM(128, return_sequences=True, input_shape=(self.sequence_length, self.features)),
            Dropout(0.2),
            LSTM(64, return_sequences=True),
            Dropout(0.2),
            LSTM(32),
            Dropout(0.2),
            Dense(16, activation='relu'),
            Dense(1)  # Output: predicted throughput
        ])
        
        model.compile(optimizer=Adam(learning_rate=0.001), 
                     loss='mse', 
                     metrics=['mae'])
        
        self.model = model
        logger.info("LSTM model built successfully")
        
    def train(self, X_train, y_train, epochs: int = 50, batch_size: int = 32):
        """Train the model"""
        if self.model is None:
            self.build_model()
            
        # Normalize features
        X_train_reshaped = X_train.reshape(-1, self.features)
        X_train_normalized = self.scaler.fit_transform(X_train_reshaped)
        X_train_normalized = X_train_normalized.reshape(-1, self.sequence_length, self.features)
        
        # Train model
        history = self.model.fit(
            X_train_normalized, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.2,
            verbose=0
        )
        
        self.is_trained = True
        logger.info(f"Model trained for {epochs} epochs")
        return history
        
    def predict(self, X) -> Tuple[float, float]:
        """Make prediction with confidence interval"""
        if not self.is_trained:
            return 0.0, 0.0
            
        # Normalize input
        X_reshaped = X.reshape(-1, self.features)
        X_normalized = self.scaler.transform(X_reshaped)
        X_normalized = X_normalized.reshape(1, self.sequence_length, self.features)
        
        # Make prediction
        prediction = self.model.predict(X_normalized, verbose=0)[0][0]
        
        # Simple confidence based on recent prediction accuracy
        confidence = 0.85  # Placeholder - implement proper confidence calculation
        
        return float(prediction), confidence
    
    def save(self, filepath: str):
        """Save model to file"""
        if self.model:
            self.model.save(f"{filepath}.h5")
            with open(f"{filepath}_scaler.pkl", 'wb') as f:
                pickle.dump(self.scaler, f)
            logger.info(f"Model saved to {filepath}")
    
    def load(self, filepath: str):
        """Load model from file"""
        try:
            self.model = load_model(f"{filepath}.h5")
            with open(f"{filepath}_scaler.pkl", 'rb') as f:
                self.scaler = pickle.load(f)
            self.is_trained = True
            logger.info(f"Model loaded from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")

class QoEPredictorXapp(RMRXapp):
    """
    QoE Predictor xApp implementation
    """
    
    def __init__(self):
        """Initialize QoE Predictor xApp"""
        super().__init__(
            default_handler=self._handle_message,
            config_handler=self._handle_config,
            rmr_port=4560,
            rmr_wait_for_ready=True,
            use_fake_sdl=False
        )
        
        # Initialize SDL
        self.sdl = SDLWrapper(use_fake_sdl=False)
        self.namespace = "qoe_predictor"
        
        # Models per cell
        self.models: Dict[str, QoEModel] = {}
        self.model_lock = Lock()
        
        # UE history tracking
        self.ue_history: Dict[str, UEHistory] = {}
        self.history_lock = Lock()
        self.max_history_length = 100
        
        # Training data buffer
        self.training_buffer = []
        self.training_buffer_size = 1000
        
        # Statistics
        self.stats = {
            "predictions_made": 0,
            "model_updates": 0,
            "accuracy": 0.0
        }
        
        # Initialize default model
        self.default_model = QoEModel()
        self.default_model.build_model()
        
        logger.info("QoE Predictor xApp initialized")
    
    def _handle_message(self, summary: dict, sbuf):
        """Handle incoming RMR messages"""
        
        mtype = summary['message type']
        logger.debug(f"Received message type: {mtype}")
        
        try:
            if mtype == QOE_PRED_REQ:
                self._handle_prediction_request(summary, sbuf)
            elif mtype == RIC_INDICATION:
                self._handle_indication(summary, sbuf)
            elif mtype == MODEL_UPDATE_REQ:
                self._handle_model_update(summary, sbuf)
            else:
                logger.warning(f"Unhandled message type: {mtype}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            
        # Free the RMR buffer
        self.rmr_free(sbuf)
    
    def _handle_prediction_request(self, summary: dict, sbuf):
        """Handle QoE prediction request"""
        
        try:
            # Parse request
            payload = json.loads(summary['payload'])
            ue_id = payload.get('ue_id')
            serving_cell = payload.get('serving_cell')
            neighbor_cells = payload.get('neighbor_cells', [])
            horizon = payload.get('prediction_horizon', 5)  # seconds
            
            # Get UE history
            ue_hist = self.ue_history.get(ue_id)
            
            if not ue_hist or len(ue_hist.throughput_history) < 20:
                # Not enough history for prediction
                self._send_prediction_response(
                    ue_id, serving_cell, neighbor_cells,
                    0.0, {}, 0.0
                )
                return
            
            # Predict serving cell QoE
            serving_qoe, serving_conf = self._predict_cell_qoe(
                ue_hist, serving_cell, horizon
            )
            
            # Predict neighbor cells QoE
            neighbor_qoe = {}
            for cell in neighbor_cells[:3]:  # Limit to top 3 neighbors
                qoe, conf = self._predict_cell_qoe(ue_hist, cell, horizon)
                neighbor_qoe[cell] = qoe
            
            # Store prediction
            prediction = QoEPrediction(
                ue_id=ue_id,
                serving_cell=serving_cell,
                neighbor_cells=neighbor_cells,
                prediction_horizon=horizon,
                serving_cell_qoe=serving_qoe,
                neighbor_cell_qoe=neighbor_qoe,
                confidence=serving_conf,
                timestamp=datetime.utcnow()
            )
            
            # Store in SDL
            key = f"prediction:{ue_id}:{serving_cell}"
            self.sdl.set(self.namespace, {key: json.dumps({
                'serving_qoe': serving_qoe,
                'neighbor_qoe': neighbor_qoe,
                'confidence': serving_conf,
                'timestamp': str(prediction.timestamp)
            })})
            
            # Send response
            self._send_prediction_response(
                ue_id, serving_cell, neighbor_cells,
                serving_qoe, neighbor_qoe, serving_conf
            )
            
            self.stats["predictions_made"] += 1
            logger.info(f"Prediction made for UE {ue_id}: {serving_qoe:.2f} Mbps")
            
        except Exception as e:
            logger.error(f"Failed to handle prediction request: {e}")
    
    def _predict_cell_qoe(self, ue_hist: UEHistory, cell_id: str, horizon: int) -> Tuple[float, float]:
        """Predict QoE for a specific cell"""
        
        # Get or create model for cell
        with self.model_lock:
            if cell_id not in self.models:
                self.models[cell_id] = QoEModel()
                # Use pre-trained weights if available
                try:
                    self.models[cell_id].load(f"/models/qoe_model_{cell_id}")
                except:
                    # Use default model
                    self.models[cell_id] = self.default_model
            
            model = self.models[cell_id]
        
        # Prepare features
        features = self._prepare_features(ue_hist)
        
        if features is None:
            return 0.0, 0.0
        
        # Make prediction
        qoe, confidence = model.predict(features)
        
        # Apply cell-specific adjustments
        if cell_id != ue_hist.cell_id:
            # Reduce QoE for non-serving cells based on handover overhead
            qoe *= 0.9
            confidence *= 0.8
        
        return qoe, confidence
    
    def _prepare_features(self, ue_hist: UEHistory) -> Optional[np.ndarray]:
        """Prepare feature matrix for prediction"""
        
        try:
            # Get last N samples
            n = min(20, len(ue_hist.throughput_history))
            
            if n < 10:  # Minimum samples needed
                return None
            
            features = np.zeros((20, 4))
            
            # Fill with available history (pad if needed)
            for i in range(n):
                features[-(n-i)] = [
                    ue_hist.throughput_history[-(n-i)],
                    ue_hist.rsrp_history[-(n-i)],
                    ue_hist.rsrq_history[-(n-i)],
                    ue_hist.cqi_history[-(n-i)]
                ]
            
            # Pad beginning with first value if needed
            if n < 20:
                for i in range(20-n):
                    features[i] = features[20-n]
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to prepare features: {e}")
            return None
    
    def _send_prediction_response(self, ue_id: str, serving_cell: str, 
                                 neighbor_cells: List[str], serving_qoe: float,
                                 neighbor_qoe: Dict[str, float], confidence: float):
        """Send prediction response"""
        
        response = {
            "ue_id": ue_id,
            "serving_cell": serving_cell,
            "neighbor_cells": neighbor_cells,
            "serving_cell_qoe": serving_qoe,
            "neighbor_cell_qoe": neighbor_qoe,
            "confidence": confidence,
            "timestamp": time.time()
        }
        
        sbuf = self.rmr_alloc()
        sbuf.contents.mtype = QOE_PRED_RESP
        sbuf.contents.payload = json.dumps(response).encode()
        sbuf.contents.len = len(sbuf.contents.payload)
        
        sbuf = self.rmr_send(sbuf, retry=True)
        
        if sbuf.contents.state == rmr.RMR_OK:
            logger.debug(f"Prediction response sent for UE {ue_id}")
    
    def _handle_indication(self, summary: dict, sbuf):
        """Handle E2 indication with UE metrics"""
        
        try:
            # Parse UE metrics from indication
            payload = json.loads(summary['payload'])
            
            for ue_data in payload.get('ue_list', []):
                ue_id = ue_data.get('ue_id')
                cell_id = ue_data.get('cell_id')
                
                # Update UE history
                with self.history_lock:
                    if ue_id not in self.ue_history:
                        self.ue_history[ue_id] = UEHistory(
                            ue_id=ue_id,
                            cell_id=cell_id,
                            throughput_history=deque(maxlen=self.max_history_length),
                            rsrp_history=deque(maxlen=self.max_history_length),
                            rsrq_history=deque(maxlen=self.max_history_length),
                            cqi_history=deque(maxlen=self.max_history_length),
                            handover_history=[]
                        )
                    
                    hist = self.ue_history[ue_id]
                    
                    # Check for handover
                    if hist.cell_id != cell_id:
                        hist.handover_history.append(
                            (datetime.utcnow(), hist.cell_id, cell_id)
                        )
                        hist.cell_id = cell_id
                    
                    # Update metrics
                    hist.throughput_history.append(ue_data.get('dl_throughput', 0))
                    hist.rsrp_history.append(ue_data.get('rsrp', -100))
                    hist.rsrq_history.append(ue_data.get('rsrq', -15))
                    hist.cqi_history.append(ue_data.get('cqi', 7))
                
                # Add to training buffer
                if len(self.training_buffer) < self.training_buffer_size:
                    self.training_buffer.append({
                        'ue_id': ue_id,
                        'cell_id': cell_id,
                        'metrics': ue_data,
                        'timestamp': time.time()
                    })
            
        except Exception as e:
            logger.error(f"Failed to handle indication: {e}")
    
    def _handle_model_update(self, summary: dict, sbuf):
        """Handle model update request"""
        
        try:
            payload = json.loads(summary['payload'])
            cell_id = payload.get('cell_id', 'default')
            
            # Train model with collected data
            if len(self.training_buffer) >= 100:
                self._train_model(cell_id)
                self.stats["model_updates"] += 1
                
                # Send response
                response = {
                    'cell_id': cell_id,
                    'status': 'success',
                    'samples_used': len(self.training_buffer)
                }
            else:
                response = {
                    'cell_id': cell_id,
                    'status': 'insufficient_data',
                    'samples_available': len(self.training_buffer)
                }
            
            sbuf_resp = self.rmr_alloc()
            sbuf_resp.contents.mtype = MODEL_UPDATE_RESP
            sbuf_resp.contents.payload = json.dumps(response).encode()
            sbuf_resp.contents.len = len(sbuf_resp.contents.payload)
            
            self.rmr_send(sbuf_resp, retry=True)
            
        except Exception as e:
            logger.error(f"Failed to handle model update: {e}")
    
    def _train_model(self, cell_id: str):
        """Train model for specific cell"""
        
        try:
            # Prepare training data from buffer
            X_train = []
            y_train = []
            
            for i in range(20, len(self.training_buffer)):
                # Use last 20 samples as features
                features = []
                for j in range(i-20, i):
                    sample = self.training_buffer[j]
                    metrics = sample['metrics']
                    features.append([
                        metrics.get('dl_throughput', 0),
                        metrics.get('rsrp', -100),
                        metrics.get('rsrq', -15),
                        metrics.get('cqi', 7)
                    ])
                
                X_train.append(features)
                # Target is next throughput value
                y_train.append(self.training_buffer[i]['metrics'].get('dl_throughput', 0))
            
            if len(X_train) < 50:
                logger.warning(f"Not enough training data for cell {cell_id}")
                return
            
            X_train = np.array(X_train)
            y_train = np.array(y_train)
            
            # Train model
            with self.model_lock:
                if cell_id not in self.models:
                    self.models[cell_id] = QoEModel()
                
                model = self.models[cell_id]
                model.train(X_train, y_train, epochs=20)
                
                # Save model
                model.save(f"/models/qoe_model_{cell_id}")
            
            logger.info(f"Model trained for cell {cell_id} with {len(X_train)} samples")
            
            # Clear training buffer
            self.training_buffer = []
            
        except Exception as e:
            logger.error(f"Failed to train model: {e}")
    
    def _handle_config(self, config: dict):
        """Handle configuration updates"""
        
        logger.info(f"Configuration updated: {config}")
        
        if 'model_params' in config:
            # Update model parameters
            params = config['model_params']
            self.default_model = QoEModel(
                sequence_length=params.get('sequence_length', 20),
                features=params.get('features', 4)
            )
            self.default_model.build_model()
    
    def start(self):
        """Start the QoE Predictor xApp"""
        
        logger.info("Starting QoE Predictor xApp")
        
        # Start training thread
        training_thread = Thread(target=self._training_loop)
        training_thread.daemon = True
        training_thread.start()
        
        # Start statistics thread
        stats_thread = Thread(target=self._stats_loop)
        stats_thread.daemon = True
        stats_thread.start()
        
        # Start RMR message loop
        self.run()
    
    def _training_loop(self):
        """Periodic model training"""
        
        while True:
            time.sleep(300)  # Train every 5 minutes
            
            if len(self.training_buffer) >= 100:
                for cell_id in list(self.models.keys()):
                    self._train_model(cell_id)
    
    def _stats_loop(self):
        """Periodic statistics reporting"""
        
        while True:
            time.sleep(60)
            logger.info(f"QoE Predictor Stats: {self.stats}")

def main():
    """Main entry point"""
    
    # Create and start xApp
    xapp = QoEPredictorXapp()
    xapp.start()

if __name__ == "__main__":
    main()
