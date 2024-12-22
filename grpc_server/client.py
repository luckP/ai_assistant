import grpc
import audio_stream_pb2_grpc
import audio_stream_pb2

def generate_audio_chunks(file_path, chunk_size=4096):
    """
    Reads the audio file in chunks and yields AudioRequest messages.
    
    Args:
        file_path (str): Path to the audio file.
        chunk_size (int): Size of each chunk in bytes.
    """
    with open(file_path, "rb") as audio_file:
        while chunk := audio_file.read(chunk_size):
            yield audio_stream_pb2.AudioRequest(audio_chunk=chunk)

def run():
    # Connect to the gRPC server
    with grpc.insecure_channel('localhost:50051') as channel:
        # Use the stub for the client
        stub = audio_stream_pb2_grpc.AudioStreamStub(channel)
        
        # Send the audio chunks
        responses = stub.StreamAudio(generate_audio_chunks("test.mp3"))
        
        # Process the server responses
        for response in responses:
            print(f"Server response: {response.transcription}")

if __name__ == "__main__":
    run()
