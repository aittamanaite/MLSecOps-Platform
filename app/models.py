"""Pydantic schemas for network flow data validation."""

from typing import List
from pydantic import BaseModel, Field


class FlowItem(BaseModel):
    """Schema representing a single network traffic flow item (33 features)."""

    flow_duration: float = Field(..., description="Duration of the flow in microseconds")
    total_fwd_packets: int = Field(..., description="Total packets in the forward direction")
    total_backward_packets: int = Field(..., description="Total packets in the backward direction")
    total_length_of_fwd_packets: float = Field(..., description="Total size of total packets in forward direction")
    total_length_of_bwd_packets: float = Field(..., description="Total size of total packets in backward direction")
    fwd_packet_length_max: float = Field(..., description="Maximum size of packet in forward direction")
    fwd_packet_length_min: float = Field(..., description="Minimum size of packet in forward direction")
    fwd_packet_length_mean: float = Field(..., description="Mean size of packet in forward direction")
    fwd_packet_length_std: float = Field(..., description="Standard deviation size of packet in forward direction")
    bwd_packet_length_max: float = Field(..., description="Maximum size of packet in backward direction")
    bwd_packet_length_min: float = Field(..., description="Minimum size of packet in backward direction")
    bwd_packet_length_mean: float = Field(..., description="Mean size of packet in backward direction")
    bwd_packet_length_std: float = Field(..., description="Standard deviation size of packet in backward direction")
    flow_bytes_s: float = Field(..., description="Flow byte rate in bytes per second")
    flow_packets_s: float = Field(..., description="Flow packet rate in packets per second")
    flow_iat_mean: float = Field(..., description="Mean time between two packets sent in flow")
    flow_iat_std: float = Field(..., description="Standard deviation time between two packets sent in flow")
    flow_iat_max: float = Field(..., description="Maximum time between two packets sent in flow")
    flow_iat_min: float = Field(..., description="Minimum time between two packets sent in flow")
    fwd_iat_total: float = Field(..., description="Total time between two packets sent in forward direction")
    fwd_iat_mean: float = Field(..., description="Mean time between two packets sent in forward direction")
    fwd_iat_std: float = Field(..., description="Standard deviation time between two packets sent in forward direction")
    fwd_iat_max: float = Field(..., description="Maximum time between two packets sent in forward direction")
    fwd_iat_min: float = Field(..., description="Minimum time between two packets sent in forward direction")
    bwd_iat_total: float = Field(..., description="Total time between two packets sent in backward direction")
    bwd_iat_mean: float = Field(..., description="Mean time between two packets sent in backward direction")
    bwd_iat_std: float = Field(..., description="Standard deviation time between two packets sent in backward direction")
    bwd_iat_max: float = Field(..., description="Maximum time between two packets sent in backward direction")
    bwd_iat_min: float = Field(..., description="Minimum time between two packets sent in backward direction")
    fwd_header_length: int = Field(..., description="Total bytes used for headers in forward direction")
    bwd_header_length: int = Field(..., description="Total bytes used for headers in backward direction")
    fwd_packets_s: float = Field(..., description="Number of forward packets per second")
    bwd_packets_s: float = Field(..., description="Number of backward packets per second")


class BatchPredictRequest(BaseModel):
    """Schema for wrapped batch prediction requests."""

    flows: List[FlowItem] = Field(..., description="List of network flows to predict in bulk")