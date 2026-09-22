/*
  Root package for MemNet SysML models — imports only; always last in config.yaml.
  MUST NOT import MemNetArchive (models/archive.sysml is off this load).
*/
package ProjectMemNet {
  private import MemNetConnections::*;
  private import MemNetRequirements::*;
  private import MemNetCousinContrast::*;
  private import MemNet::*;
  // TipMemNetAccessPortal is in package MemNet, outside MemNetSystem
  // (same import as MemNetUsageDashboard / MemNetOpsFleet). tip≠face.
  private import MemNetImplementation::*;
  private import MemNetBehaviour::*;
  private import MemNetVerification::*;
}
