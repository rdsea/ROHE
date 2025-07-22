import os
import sys
parent_dir = os.path.abspath(os.path.join(os.getcwd(), '..', '..'))
sys.path.append(parent_dir)
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
from rohe.common.rohe_utils import find_all_files_in_mmact
import numpy as np
import traceback
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torch.cuda.amp import autocast, GradScaler  # Add mixed precision support
import cv2
from torchvision.transforms import Compose
from pytorchvideo.models.x3d import create_x3d
from sklearn.metrics import classification_report
import yaml
import argparse

# load environment variables
DATA_PATH = os.getenv('DATA_PATH')

VIDEO_DIR = os.path.join(DATA_PATH, 'mmact/trimmed_video/')
print(f"Video directory: {VIDEO_DIR}")

mp4_file_path_list, mp4_file_info_list = find_all_files_in_mmact(VIDEO_DIR, '.mp4')

# Check if CUDA is available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# X3D model configurations
X3D_CONFIGS = {}

class VideoDataset(Dataset):
    def __init__(self, video_paths, labels, transform=None, clip_length=16):
        self.video_paths = video_paths
        self.labels = labels
        self.transform = transform
        self.clip_length = clip_length
        
    def __len__(self):
        return len(self.video_paths)
    
    def __getitem__(self, idx):
        video_path = self.video_paths[idx]
        label = self.labels[idx]
        
        # Load video
        video = self.load_video(video_path)
        
        if self.transform:
            video = self.transform(video)
            
        return video, label
    
    def load_video(self, video_path):
        """Load video and convert to tensor format with well-distributed frame sampling"""
        cap = cv2.VideoCapture(video_path)
        
        # Get video properties for better memory allocation
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Sample frames evenly across the video duration
        if total_frames > 0:
            # Create evenly distributed frame indices throughout the video
            if total_frames >= self.clip_length:
                # Sample frames evenly across the entire video duration
                frame_indices = np.linspace(0, total_frames - 1, self.clip_length).astype(int)
            else:
                # For very short videos, take all frames and repeat as needed
                frame_indices = np.arange(total_frames)
        else:
            # Fallback if frame count is unavailable
            frame_indices = None
        
        frames = []
        
        if frame_indices is not None:
            # Efficient frame extraction by seeking to specific frames
            frame_indices_set = set(frame_indices)  # O(1) lookup
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Only process frames we need for sampling
                if frame_count in frame_indices_set:
                    # Convert BGR to RGB
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append(frame)
                    
                    # Early exit if we have enough frames
                    if len(frames) >= self.clip_length:
                        break
                
                frame_count += 1
        else:
            # Fallback: read all frames if frame count is unreliable
            all_frames = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                all_frames.append(frame)
            
            # Sample evenly from loaded frames
            if len(all_frames) >= self.clip_length:
                indices = np.linspace(0, len(all_frames) - 1, self.clip_length).astype(int)
                frames = [all_frames[i] for i in indices]
            else:
                frames = all_frames
        
        cap.release()
        
        # Handle videos shorter than required clip length
        if len(frames) < self.clip_length:
            # Repeat frames cyclically to maintain temporal distribution
            original_frames = frames.copy()
            while len(frames) < self.clip_length:
                remaining_needed = self.clip_length - len(frames)
                frames.extend(original_frames[:min(len(original_frames), remaining_needed)])
        
        # Ensure exact clip length (trim if somehow we have too many)
        frames = frames[:self.clip_length]
        
        # Convert to tensor more efficiently using numpy
        frames_array = np.stack(frames, axis=0)  # (T, H, W, C)
        video_tensor = torch.from_numpy(frames_array).float()
        video_tensor = video_tensor.permute(3, 0, 1, 2)  # (C, T, H, W)
        
        return video_tensor


class NormalizeToFloat:
    """Convert to float and normalize to [0, 1]"""
    def __call__(self, x):
        return x / 255.0

class ResizeVideo:
    """Resize video to target dimensions"""
    def __init__(self, config):
        self.config = config
    
    def __call__(self, x):
        return torch.nn.functional.interpolate(
            x.unsqueeze(0), 
            size=(self.config['input_clip_length'], self.config['input_crop_size'], self.config['input_crop_size']),
            mode='trilinear',
            align_corners=False
        ).squeeze(0)

class NormalizeWithStats:
    """Normalize with ImageNet statistics"""
    def __init__(self, config):
        self.mean = torch.tensor(config['mean']).view(3, 1, 1, 1)
        self.std = torch.tensor(config['std']).view(3, 1, 1, 1)
    
    def __call__(self, x):
        return (x - self.mean) / self.std

def create_transforms(config):
    """Create transforms for X3D model"""
    return Compose([
        NormalizeToFloat(),
        ResizeVideo(config),
        NormalizeWithStats(config)
    ])
    


def prepare_video_data(mp4_file_info_list):
    """Prepare video data and create label mapping"""
    video_paths = []
    labels = []
    label_names = []
    
    for file_info in mp4_file_info_list:
        video_path = file_info['file_path']
        
        label_name = file_info['label']
        
        video_paths.append(video_path)
        label_names.append(label_name)
    
    # Create label mapping
    unique_labels = sorted(list(set(label_names)))
    label_to_idx = {label: idx for idx, label in enumerate(unique_labels)}
    idx_to_label = {idx: label for label, idx in label_to_idx.items()}
    
    # Convert label names to indices
    labels = [label_to_idx[label_name] for label_name in label_names]
    
    return video_paths, labels, label_to_idx, idx_to_label

def create_x3d_model(model_size, num_classes):
    """Create X3D model of specified size"""
    config = X3D_CONFIGS[model_size]
    
    # Create the model
    model = create_x3d(
        input_channel=3,
        input_clip_length=config['input_clip_length'],
        input_crop_size=config['input_crop_size'],
        model_num_class=num_classes
    )
    
    return model.to(device)

def train_x3d_model(model, model_size, train_loader, val_loader, num_epochs=10, learning_rate=0.001):
    """Train X3D model with optimized GPU utilization"""
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)
    
    train_losses = []
    val_accuracies = []
    
    scaler = GradScaler() if USE_MIXED_PRECISION else None
    
    for epoch in range(num_epochs):
        # Training phase
        model.train()
        running_loss = 0.0
        optimizer.zero_grad()  # Zero gradients at start of epoch
        
        for batch_idx, (videos, labels) in enumerate(train_loader):
            videos, labels = videos.to(device, non_blocking=True), labels.to(device, non_blocking=True)
            
            # Use mixed precision if enabled
            if USE_MIXED_PRECISION and scaler:
                with autocast():
                    outputs = model(videos)
                    loss = criterion(outputs, labels) / GRADIENT_ACCUMULATION_STEPS[model_size]
                
                scaler.scale(loss).backward()
                
                # Gradient accumulation
                if (batch_idx + 1) % GRADIENT_ACCUMULATION_STEPS[model_size] == 0:
                    scaler.step(optimizer)
                    scaler.update()
                    optimizer.zero_grad()
            else:
                outputs = model(videos)
                loss = criterion(outputs, labels) / GRADIENT_ACCUMULATION_STEPS[model_size]
                loss.backward()
                
                # Gradient accumulation
                if (batch_idx + 1) % GRADIENT_ACCUMULATION_STEPS[model_size] == 0:
                    optimizer.step()
                    optimizer.zero_grad()

            running_loss += loss.item() * GRADIENT_ACCUMULATION_STEPS[model_size]

            if batch_idx % (10 * GRADIENT_ACCUMULATION_STEPS[model_size]) == 0:
                print(f'Epoch {epoch+1}/{num_epochs}, Batch {batch_idx}, Loss: {loss.item() * GRADIENT_ACCUMULATION_STEPS[model_size]:.4f}')

        # Handle remaining gradients if batch count not divisible by accumulation steps
        if len(train_loader) % GRADIENT_ACCUMULATION_STEPS[model_size] != 0:
            if USE_MIXED_PRECISION and scaler:
                scaler.step(optimizer)
                scaler.update()
            else:
                optimizer.step()
            optimizer.zero_grad()
        
        # Validation phase
        model.eval()
        correct = 0
        total = 0
        val_loss = 0.0
        
        with torch.no_grad():
            for videos, labels in val_loader:
                videos, labels = videos.to(device, non_blocking=True), labels.to(device, non_blocking=True)
                
                if USE_MIXED_PRECISION:
                    with autocast():
                        outputs = model(videos)
                        loss = criterion(outputs, labels)
                else:
                    outputs = model(videos)
                    loss = criterion(outputs, labels)
                
                val_loss += loss.item()
                
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        
        epoch_train_loss = running_loss / len(train_loader)
        epoch_val_acc = 100 * correct / total
        
        train_losses.append(epoch_train_loss)
        val_accuracies.append(epoch_val_acc)
        
        print(f'Epoch {epoch+1}/{num_epochs}:')
        print(f'  Train Loss: {epoch_train_loss:.4f}')
        print(f'  Val Accuracy: {epoch_val_acc:.2f}%')
        print('-' * 50)
        
        scheduler.step()
    
    return model, train_losses, val_accuracies




# Training parameters
BATCH_SIZE = {
    'XS': 64,
    'S': 24,
    'M': 8,
    'L': 2
}  # Increased for better GPU utilization
EFFECTIVE_BATCH_SIZE = {
    'XS': 128,
    'S': 48,
    'M': 16,
    'L': 4
}
GRADIENT_ACCUMULATION_STEPS = {
    'XS': EFFECTIVE_BATCH_SIZE['XS'] // BATCH_SIZE['XS'],
    'S': EFFECTIVE_BATCH_SIZE['S'] // BATCH_SIZE['S'],
    'M': EFFECTIVE_BATCH_SIZE['M'] // BATCH_SIZE['M'],
    'L': EFFECTIVE_BATCH_SIZE['L'] // BATCH_SIZE['L']
}
NUM_WORKERS = 8  # Increased for faster data loading
NUM_EPOCHS = 2
LEARNING_RATE = 0.001
NUM_VERSIONS = 1  # Train 1 version of each model size
USE_MIXED_PRECISION = True  # Enable mixed precision training for speed


def get_optimal_batch_size(model, sample_input, device, max_batch_size=2048):
    """
    Determine optimal batch size based on available GPU memory
    """
    model.eval()
    optimal_batch_size = 1
    
    for batch_size in [2, 4, 8, 16, 24, 32, 64, 128, 256]:
        if batch_size > max_batch_size:
            break
            
        try:
            # Create a batch of the given size
            batch_input = sample_input.unsqueeze(0).repeat(batch_size, 1, 1, 1, 1)
            batch_input = batch_input.to(device)
            
            # Try forward pass
            with torch.no_grad():
                _ = model(batch_input)
            
            optimal_batch_size = batch_size
            print(f"Batch size {batch_size}: OK")
            
            # Clean up
            del batch_input
            torch.cuda.empty_cache()
            
        except RuntimeError as e:
            if "out of memory" in str(e):
                print(f"Batch size {batch_size}: Out of memory")
                break
            else:
                raise e
    
    return optimal_batch_size

def monitor_gpu_usage():
    """Monitor GPU memory usage for optimization"""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3  # GB
        reserved = torch.cuda.memory_reserved() / 1024**3   # GB
        max_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
        
        print(f"GPU Memory - Allocated: {allocated:.2f}GB, Reserved: {reserved:.2f}GB, Total: {max_memory:.2f}GB")
        print(f"GPU Utilization: {allocated/max_memory*100:.1f}%")
        return allocated/max_memory
    return 0


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description="Train X3D models on video data")
    argparser.add_argument('--config', type=str, default='x3d_config.yaml',
                           help='Path to X3D configuration file')
    args = argparser.parse_args()
    # Load X3D configurations from YAML file
    with open(args.config, 'r') as f:
        X3D_CONFIGS = yaml.safe_load(f)
    # Prepare video data
    print("Preparing video data...")
    video_paths, labels, label_to_idx, idx_to_label = prepare_video_data(mp4_file_info_list)
    num_classes = len(label_to_idx)

    print(f"Total videos: {len(video_paths)}")
    print(f"Number of classes: {num_classes}")
    print(f"Classes: {list(label_to_idx.keys())}")
    
    # Convert to numpy arrays
    video_paths = np.array(video_paths)
    labels = np.array(labels)
    
    # Train models for each X3D size
    for model_size in ['M', 'L']:
        print(f"\n{'='*60}")
        print(f"Training X3D-{model_size} models")
        print(f"{'='*60}")
        
        config = X3D_CONFIGS[model_size]
        
        # Test optimal batch size for this model configuration
        print("Determining optimal batch size...")
        test_model = create_x3d_model(model_size, num_classes)
        
        # Create a sample input
        sample_video = torch.randn(3, config['input_clip_length'], 
                                 config['input_crop_size'], config['input_crop_size'])
        
        optimal_batch = get_optimal_batch_size(test_model, sample_video, device)
        
        # Update batch size if we found a better one
        actual_batch_size = min(optimal_batch, BATCH_SIZE[model_size])
        if actual_batch_size != BATCH_SIZE[model_size]:
            print(f"Adjusting batch size from {BATCH_SIZE[model_size]} to {actual_batch_size} for better GPU utilization")
        else:
            actual_batch_size = BATCH_SIZE[model_size]

        # Clean up test model
        del test_model, sample_video
        torch.cuda.empty_cache()
        
        for version in range(NUM_VERSIONS):
            print(f"\nTraining X3D-{model_size} version {version + 1}/{NUM_VERSIONS}")
            print("-" * 40)
            
            try:
                # Create different train/test splits for each version
                train_indices = np.random.choice(len(video_paths), size=int(0.8 * len(video_paths)), replace=False)
                test_indices = np.setdiff1d(np.arange(len(video_paths)), train_indices)
                
                # Further split train into train/val
                val_size = int(0.2 * len(train_indices))
                val_indices = train_indices[:val_size]
                train_indices = train_indices[val_size:]
                
                print(f"Train samples: {len(train_indices)}")
                print(f"Validation samples: {len(val_indices)}")
                print(f"Test samples: {len(test_indices)}")
                
                # Create transforms
                transform = create_transforms(config)
                
                # Create datasets
                train_dataset = VideoDataset(
                    video_paths[train_indices], 
                    labels[train_indices], 
                    transform=transform, 
                    clip_length=config['input_clip_length']
                )
                val_dataset = VideoDataset(
                    video_paths[val_indices], 
                    labels[val_indices], 
                    transform=transform, 
                    clip_length=config['input_clip_length']
                )
                test_dataset = VideoDataset(
                    video_paths[test_indices], 
                    labels[test_indices], 
                    transform=transform, 
                    clip_length=config['input_clip_length']
                )
                
                # Create data loaders with optimized settings
                train_loader = DataLoader(
                    train_dataset, 
                    batch_size=actual_batch_size, 
                    shuffle=True, 
                    num_workers=NUM_WORKERS,
                    pin_memory=True,  # Faster data transfer to GPU
                    persistent_workers=True if NUM_WORKERS > 0 else False,  # Keep workers alive
                    prefetch_factor=2  # Prefetch batches for better pipeline
                )
                val_loader = DataLoader(
                    val_dataset, 
                    batch_size=actual_batch_size, 
                    shuffle=False, 
                    num_workers=NUM_WORKERS,
                    pin_memory=True,
                    persistent_workers=True if NUM_WORKERS > 0 else False,
                    prefetch_factor=2
                )
                test_loader = DataLoader(
                    test_dataset, 
                    batch_size=actual_batch_size, 
                    shuffle=False, 
                    num_workers=NUM_WORKERS,
                    pin_memory=True,
                    persistent_workers=True if NUM_WORKERS > 0 else False,
                    prefetch_factor=2
                )
                
                # Create model
                model = create_x3d_model(model_size, num_classes)
                print(f"Created X3D-{model_size} model with {sum(p.numel() for p in model.parameters())} parameters")
                
                # Monitor initial GPU usage
                print("\nInitial GPU usage:")
                monitor_gpu_usage()
                
                # Train model
                trained_model, train_losses, val_accuracies = train_x3d_model(
                    model, model_size, train_loader, val_loader, NUM_EPOCHS, LEARNING_RATE
                )
                
                # Monitor final GPU usage
                print("\nFinal GPU usage:")
                monitor_gpu_usage()
                
                # Test the model
                trained_model.eval()
                test_correct = 0
                test_total = 0
                all_predictions = []
                all_labels = []
                
                with torch.no_grad():
                    for videos, labels_batch in test_loader:
                        videos, labels_batch = videos.to(device, non_blocking=True), labels_batch.to(device, non_blocking=True)
                        outputs = trained_model(videos)
                        _, predicted = torch.max(outputs, 1)
                        
                        test_total += labels_batch.size(0)
                        test_correct += (predicted == labels_batch).sum().item()
                        
                        all_predictions.extend(predicted.cpu().numpy())
                        all_labels.extend(labels_batch.cpu().numpy())
                
                test_accuracy = 100 * test_correct / test_total
                print(f"\nFinal Test Accuracy: {test_accuracy:.2f}%")
                
                # Save model and results
                model_dir = f"./X3D_{model_size}/"
                if not os.path.exists(model_dir):
                    os.makedirs(model_dir)
                
                version_dir = f"{model_dir}v{version + 1}/"
                if not os.path.exists(version_dir):
                    os.makedirs(version_dir)
                
                # Save model
                torch.save(trained_model.state_dict(), f"{version_dir}model.pth")
                
                # Save training results as simple data types only
                results = {
                    'model_size': model_size,
                    'version': version + 1,
                    'input_clip_length': config['input_clip_length'],
                    'input_crop_size': config['input_crop_size'],
                    'mean': config['mean'],
                    'std': config['std'],
                    'train_losses': train_losses,
                    'val_accuracies': val_accuracies,
                    'test_accuracy': test_accuracy,
                    'label_to_idx': label_to_idx,
                    'idx_to_label': idx_to_label,
                    'num_classes': num_classes,
                    'train_indices': train_indices.tolist(),
                    'val_indices': val_indices.tolist(),
                    'test_indices': test_indices.tolist()
                }
                
                # Save as JSON (more reliable and readable)
                import json
                with open(f"{version_dir}training_results.json", 'w') as f:
                    json.dump(results, f, indent=2)
                
                # Save classification report
                report = classification_report(all_labels, all_predictions, 
                                            target_names=[idx_to_label[i] for i in range(num_classes)])
                with open(f"{version_dir}classification_report.txt", 'w') as f:
                    f.write(report)
                
                print(f"Model X3D-{model_size}_v{version + 1} saved successfully!")
                print(f"Files saved in: {version_dir}")
                
                # Clean up
                del trained_model, train_loader, val_loader, test_loader
                torch.cuda.empty_cache()
                
                
            except Exception as e:
                print(f"Error training X3D-{model_size}_v{version + 1}: {str(e)}")
                print(f"Traceback: {traceback.format_exc()}")
                continue

    print("\n" + "="*60)
    print("Training completed for all X3D model sizes!")
    print("="*60)
