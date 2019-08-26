# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: ethaergo_bridge_operator/bridge_operator.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='ethaergo_bridge_operator/bridge_operator.proto',
  package='',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=_b('\n.ethaergo_bridge_operator/bridge_operator.proto\"A\n\x06\x41nchor\x12\x0c\n\x04root\x18\x01 \x01(\x0c\x12\x0e\n\x06height\x18\x02 \x01(\x04\x12\x19\n\x11\x64\x65stination_nonce\x18\x03 \x01(\x04\"7\n\x08\x41pproval\x12\x0f\n\x07\x61\x64\x64ress\x18\x01 \x01(\t\x12\x0b\n\x03sig\x18\x02 \x01(\x0c\x12\r\n\x05\x65rror\x18\x03 \x01(\t\"4\n\x08NewTempo\x12\r\n\x05tempo\x18\x01 \x01(\x04\x12\x19\n\x11\x64\x65stination_nonce\x18\x02 \x01(\x04\">\n\rNewValidators\x12\x12\n\nvalidators\x18\x01 \x03(\t\x12\x19\n\x11\x64\x65stination_nonce\x18\x02 \x01(\x04\"8\n\x0eNewUnfreezeFee\x12\x0b\n\x03\x66\x65\x65\x18\x01 \x01(\x04\x12\x19\n\x11\x64\x65stination_nonce\x18\x02 \x01(\x04\x32\xee\x03\n\x0e\x42ridgeOperator\x12-\n\x15GetEthAnchorSignature\x12\x07.Anchor\x1a\t.Approval\"\x00\x12/\n\x17GetAergoAnchorSignature\x12\x07.Anchor\x1a\t.Approval\"\x00\x12\x30\n\x16GetEthTAnchorSignature\x12\t.NewTempo\x1a\t.Approval\"\x00\x12/\n\x15GetEthTFinalSignature\x12\t.NewTempo\x1a\t.Approval\"\x00\x12\x32\n\x18GetAergoTAnchorSignature\x12\t.NewTempo\x1a\t.Approval\"\x00\x12\x31\n\x17GetAergoTFinalSignature\x12\t.NewTempo\x1a\t.Approval\"\x00\x12\x38\n\x19GetEthValidatorsSignature\x12\x0e.NewValidators\x1a\t.Approval\"\x00\x12:\n\x1bGetAergoValidatorsSignature\x12\x0e.NewValidators\x1a\t.Approval\"\x00\x12<\n\x1cGetAergoUnfreezeFeeSignature\x12\x0f.NewUnfreezeFee\x1a\t.Approval\"\x00\x62\x06proto3')
)




_ANCHOR = _descriptor.Descriptor(
  name='Anchor',
  full_name='Anchor',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='root', full_name='Anchor.root', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='height', full_name='Anchor.height', index=1,
      number=2, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='destination_nonce', full_name='Anchor.destination_nonce', index=2,
      number=3, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=50,
  serialized_end=115,
)


_APPROVAL = _descriptor.Descriptor(
  name='Approval',
  full_name='Approval',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='address', full_name='Approval.address', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='sig', full_name='Approval.sig', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='error', full_name='Approval.error', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=117,
  serialized_end=172,
)


_NEWTEMPO = _descriptor.Descriptor(
  name='NewTempo',
  full_name='NewTempo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='tempo', full_name='NewTempo.tempo', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='destination_nonce', full_name='NewTempo.destination_nonce', index=1,
      number=2, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=174,
  serialized_end=226,
)


_NEWVALIDATORS = _descriptor.Descriptor(
  name='NewValidators',
  full_name='NewValidators',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='validators', full_name='NewValidators.validators', index=0,
      number=1, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='destination_nonce', full_name='NewValidators.destination_nonce', index=1,
      number=2, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=228,
  serialized_end=290,
)


_NEWUNFREEZEFEE = _descriptor.Descriptor(
  name='NewUnfreezeFee',
  full_name='NewUnfreezeFee',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='fee', full_name='NewUnfreezeFee.fee', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='destination_nonce', full_name='NewUnfreezeFee.destination_nonce', index=1,
      number=2, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=292,
  serialized_end=348,
)

DESCRIPTOR.message_types_by_name['Anchor'] = _ANCHOR
DESCRIPTOR.message_types_by_name['Approval'] = _APPROVAL
DESCRIPTOR.message_types_by_name['NewTempo'] = _NEWTEMPO
DESCRIPTOR.message_types_by_name['NewValidators'] = _NEWVALIDATORS
DESCRIPTOR.message_types_by_name['NewUnfreezeFee'] = _NEWUNFREEZEFEE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Anchor = _reflection.GeneratedProtocolMessageType('Anchor', (_message.Message,), {
  'DESCRIPTOR' : _ANCHOR,
  '__module__' : 'ethaergo_bridge_operator.bridge_operator_pb2'
  # @@protoc_insertion_point(class_scope:Anchor)
  })
_sym_db.RegisterMessage(Anchor)

Approval = _reflection.GeneratedProtocolMessageType('Approval', (_message.Message,), {
  'DESCRIPTOR' : _APPROVAL,
  '__module__' : 'ethaergo_bridge_operator.bridge_operator_pb2'
  # @@protoc_insertion_point(class_scope:Approval)
  })
_sym_db.RegisterMessage(Approval)

NewTempo = _reflection.GeneratedProtocolMessageType('NewTempo', (_message.Message,), {
  'DESCRIPTOR' : _NEWTEMPO,
  '__module__' : 'ethaergo_bridge_operator.bridge_operator_pb2'
  # @@protoc_insertion_point(class_scope:NewTempo)
  })
_sym_db.RegisterMessage(NewTempo)

NewValidators = _reflection.GeneratedProtocolMessageType('NewValidators', (_message.Message,), {
  'DESCRIPTOR' : _NEWVALIDATORS,
  '__module__' : 'ethaergo_bridge_operator.bridge_operator_pb2'
  # @@protoc_insertion_point(class_scope:NewValidators)
  })
_sym_db.RegisterMessage(NewValidators)

NewUnfreezeFee = _reflection.GeneratedProtocolMessageType('NewUnfreezeFee', (_message.Message,), {
  'DESCRIPTOR' : _NEWUNFREEZEFEE,
  '__module__' : 'ethaergo_bridge_operator.bridge_operator_pb2'
  # @@protoc_insertion_point(class_scope:NewUnfreezeFee)
  })
_sym_db.RegisterMessage(NewUnfreezeFee)



_BRIDGEOPERATOR = _descriptor.ServiceDescriptor(
  name='BridgeOperator',
  full_name='BridgeOperator',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  serialized_start=351,
  serialized_end=845,
  methods=[
  _descriptor.MethodDescriptor(
    name='GetEthAnchorSignature',
    full_name='BridgeOperator.GetEthAnchorSignature',
    index=0,
    containing_service=None,
    input_type=_ANCHOR,
    output_type=_APPROVAL,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='GetAergoAnchorSignature',
    full_name='BridgeOperator.GetAergoAnchorSignature',
    index=1,
    containing_service=None,
    input_type=_ANCHOR,
    output_type=_APPROVAL,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='GetEthTAnchorSignature',
    full_name='BridgeOperator.GetEthTAnchorSignature',
    index=2,
    containing_service=None,
    input_type=_NEWTEMPO,
    output_type=_APPROVAL,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='GetEthTFinalSignature',
    full_name='BridgeOperator.GetEthTFinalSignature',
    index=3,
    containing_service=None,
    input_type=_NEWTEMPO,
    output_type=_APPROVAL,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='GetAergoTAnchorSignature',
    full_name='BridgeOperator.GetAergoTAnchorSignature',
    index=4,
    containing_service=None,
    input_type=_NEWTEMPO,
    output_type=_APPROVAL,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='GetAergoTFinalSignature',
    full_name='BridgeOperator.GetAergoTFinalSignature',
    index=5,
    containing_service=None,
    input_type=_NEWTEMPO,
    output_type=_APPROVAL,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='GetEthValidatorsSignature',
    full_name='BridgeOperator.GetEthValidatorsSignature',
    index=6,
    containing_service=None,
    input_type=_NEWVALIDATORS,
    output_type=_APPROVAL,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='GetAergoValidatorsSignature',
    full_name='BridgeOperator.GetAergoValidatorsSignature',
    index=7,
    containing_service=None,
    input_type=_NEWVALIDATORS,
    output_type=_APPROVAL,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='GetAergoUnfreezeFeeSignature',
    full_name='BridgeOperator.GetAergoUnfreezeFeeSignature',
    index=8,
    containing_service=None,
    input_type=_NEWUNFREEZEFEE,
    output_type=_APPROVAL,
    serialized_options=None,
  ),
])
_sym_db.RegisterServiceDescriptor(_BRIDGEOPERATOR)

DESCRIPTOR.services_by_name['BridgeOperator'] = _BRIDGEOPERATOR

# @@protoc_insertion_point(module_scope)
