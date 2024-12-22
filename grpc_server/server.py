import grpc
from concurrent import futures
import audio_stream_pb2_grpc
import audio_stream_pb2

# Implement the service
class AudioStreamServicer(audio_stream_pb2_grpc.AudioStreamServicer):
    def StreamAudio(self, request_iterator, context):
        for audio_request in request_iterator:
            print("Received audio chunk")
            # Dummy transcription for demonstration purposes
            yield audio_stream_pb2.AudioResponse(transcription="Transcribed audio")

# Start the gRPC server
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    audio_stream_pb2_grpc.add_AudioStreamServicer_to_server(AudioStreamServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC server is running on port 50051")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
