# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

from unfreeze_service import unfreeze_service_pb2 as unfreeze__service_dot_unfreeze__service__pb2


class UnfreezeServiceStub(object):
  # missing associated documentation comment in .proto file
  pass

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.RequestUnfreeze = channel.unary_unary(
        '/UnfreezeService/RequestUnfreeze',
        request_serializer=unfreeze__service_dot_unfreeze__service__pb2.AccountRef.SerializeToString,
        response_deserializer=unfreeze__service_dot_unfreeze__service__pb2.Status.FromString,
        )


class UnfreezeServiceServicer(object):
  # missing associated documentation comment in .proto file
  pass

  def RequestUnfreeze(self, request, context):
    """Request unfreezing
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_UnfreezeServiceServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'RequestUnfreeze': grpc.unary_unary_rpc_method_handler(
          servicer.RequestUnfreeze,
          request_deserializer=unfreeze__service_dot_unfreeze__service__pb2.AccountRef.FromString,
          response_serializer=unfreeze__service_dot_unfreeze__service__pb2.Status.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'UnfreezeService', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
