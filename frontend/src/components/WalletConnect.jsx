import React, { useState } from 'react'
import { ethers } from 'ethers'

export default function WalletConnect() {
  const [address, setAddress] = useState('')

  const connect = async () => {
    if (!window.ethereum) return alert('Please install MetaMask')
    const provider = new ethers.BrowserProvider(window.ethereum)
    const accounts = await provider.send('eth_requestAccounts', [])
    setAddress(accounts[0])
  }

  const short = addr => addr ? `${addr.slice(0, 6)}...${addr.slice(-4)}` : ''

  return (
    <button onClick={connect} style={{
      padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
      background: address ? '#166534' : '#1d4ed8', color: '#fff', fontWeight: 600,
    }}>
      {address ? short(address) : 'Connect Wallet'}
    </button>
  )
}
