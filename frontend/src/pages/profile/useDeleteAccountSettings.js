import { useState } from 'react'

export function useDeleteAccountSettings({ deleteAccount, logout, navigate }) {
  const [isDeleteOpen, setIsDeleteOpen] = useState(false)
  const [deleteConfirmation, setDeleteConfirmation] = useState('')
  const [deleteStatus, setDeleteStatus] = useState('idle')
  const [deleteError, setDeleteError] = useState('')

  function openDeleteModal() {
    setDeleteConfirmation('')
    setDeleteError('')
    setIsDeleteOpen(true)
  }

  const handleDeleteAccount = async (event) => {
    event.preventDefault()

    if (deleteConfirmation.trim().toLowerCase() !== 'delete') {
      setDeleteError('Type delete to confirm.')
      return
    }

    setDeleteStatus('deleting')
    setDeleteError('')

    try {
      await deleteAccount(deleteConfirmation)
      setDeleteStatus('success')
      window.setTimeout(() => {
        logout().finally(() => {
          navigate('/', { replace: true })
        })
      }, 1100)
    } catch (requestError) {
      setDeleteError(
        requestError instanceof Error ? requestError.message : 'Unable to delete account.',
      )
      setDeleteStatus('idle')
    }
  }

  return {
    deleteConfirmation,
    deleteError,
    deleteStatus,
    handleDeleteAccount,
    isDeleteOpen,
    openDeleteModal,
    setDeleteConfirmation,
    setIsDeleteOpen,
  }
}
