import React, { useContext } from 'react';
import { AuthContext } from '../../context/AuthContext';
import MerchantSideBar from '../Merchant/SideBar';
import AdminSideBar from '../Admin/SideBar';
import ClerkSideBar from '../Clerk/SideBar';

const SideBar = () => {
  const { user } = useContext(AuthContext);

  if (!user) return null;

  switch (user.role) {
    case 'MERCHANT':
      return <MerchantSideBar />;
    case 'ADMIN':
      return <AdminSideBar />;
    case 'CLERK':
      return <ClerkSideBar />;
    default:
      return null;
  }
};

export default SideBar;