// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract FaceVerificationRegistry {
    struct Record { bytes32 fingerprint; address submitter; uint64 timestamp; string matchedUrl; }
    mapping(bytes32 => Record) public records;
    event Stored(bytes32 indexed fingerprint, address indexed submitter, uint64 timestamp, string matchedUrl);

    function storeRecord(bytes32 fp, string calldata url) external {
        require(records[fp].timestamp == 0, "exists");
        records[fp] = Record(fp, msg.sender, uint64(block.timestamp), url);
        emit Stored(fp, msg.sender, uint64(block.timestamp), url);
    }
    function getRecord(bytes32 fp) external view returns (Record memory) { return records[fp]; }
}
