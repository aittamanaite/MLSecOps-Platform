"""Pydantic schemas for network flow data validation."""
from typing import List
from pydantic import BaseModel, Field


class FlowItem(BaseModel):
    """Schema representing a single network traffic flow item """

    flow_duration: float = Field(..., description="Duration of the flow in microseconds")
    total_fwd_packets: int = Field(..., description="Total packets in the forward direction")
    total_backward_packets: int = Field(..., description="Total packets in the backward direction")
    total_length_of_fwd_packets: float = Field(..., description="Total size of packets in forward direction")
    total_length_of_bwd_packets: float = Field(..., description="Total size of packets in backward direction")
    fwd_packet_length_max: float = Field(..., description="Maximum size of packet in forward direction")
    fwd_packet_length_min: float = Field(..., description="Minimum size of packet in forward direction")
    fwd_packet_length_mean: float = Field(..., description="Mean size of packet in forward direction")
    fwd_packet_length_std: float = Field(..., description="Standard deviation size of packet in forward direction")
    bwd_packet_length_max: float = Field(..., description="Maximum size of packet in backward direction")
    bwd_packet_length_min: float = Field(..., description="Minimum size of packet in backward direction")
    bwd_packet_length_mean: float = Field(..., description="Mean size of packet in backward direction")
    bwd_packet_length_std: float = Field(..., description="Standard deviation size of packet in backward direction")
    flow_iat_mean: float = Field(..., description="Mean time between two packets sent in flow")
    flow_iat_std: float = Field(..., description="Standard deviation time between two packets sent in flow")
    flow_iat_max: float = Field(..., description="Maximum time between two packets sent in flow")
    flow_iat_min: float = Field(..., description="Minimum time between two packets sent in flow")
    fwd_iat_total: float = Field(..., description="Total time between two packets sent in forward direction")
    fwd_iat_mean: float = Field(..., description="Mean time between two packets sent in forward direction")
    fwd_iat_std: float = Field(..., description="Std dev time between two packets sent in forward direction")
    bwd_iat_total: float = Field(..., description="Total time between two packets sent in backward direction")
    bwd_iat_mean: float = Field(..., description="Mean time between two packets sent in backward direction")
    bwd_iat_std: float = Field(..., description="Std dev time between two packets sent in backward direction")
    fin_flag_count: int = Field(..., description="Number of packets with FIN flag set")
    syn_flag_count: int = Field(..., description="Number of packets with SYN flag set")
    rst_flag_count: int = Field(..., description="Number of packets with RST flag set")
    psh_flag_count: int = Field(..., description="Number of packets with PSH flag set")
    ack_flag_count: int = Field(..., description="Number of packets with ACK flag set")
    average_packet_size: float = Field(..., description="Average size of a packet in the flow")
    active_mean: float = Field(..., description="Mean time a flow was active before going idle")
    active_std: float = Field(..., description="Std dev of time a flow was active before going idle")
    idle_mean: float = Field(..., description="Mean time a flow was idle before becoming active")
    idle_std: float = Field(..., description="Std dev of time a flow was idle before becoming active")


class BatchPredictRequest(BaseModel):
    """Schema for wrapped batch prediction requests."""

    flows: List[FlowItem] = Field(..., description="List of network flows to predict in bulk")