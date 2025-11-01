
import React from 'react';
import { useCart } from '../contexts/CartContext';
import { CartIcon } from './Icons';

interface FloatingCartButtonProps {
    setView: (view: 'cart') => void;
}

const FloatingCartButton: React.FC<FloatingCartButtonProps> = ({ setView }) => {
    const { totalItems, totalPrice } = useCart();

    if (totalItems === 0) return null;

    return (
        <div className="fixed bottom-0 left-0 right-0 p-4 bg-transparent z-20">
            <button
                onClick={() => setView('cart')}
                className="w-full max-w-md mx-auto flex items-center justify-between p-3 bg-primary text-primary-text rounded-xl shadow-lg hover:opacity-90 transition-opacity"
            >
                <div className="flex items-center">
                    <div className="relative">
                        <CartIcon className="w-6 h-6" />
                        <span className="absolute -top-2 -right-2 flex items-center justify-center w-5 h-5 text-xs font-bold bg-white text-primary rounded-full">
                            {totalItems}
                        </span>
                    </div>
                    <span className="ml-3 font-semibold text-lg">View Cart</span>
                </div>
                <span className="font-bold text-lg">${totalPrice.toFixed(2)}</span>
            </button>
        </div>
    );
};

export default FloatingCartButton;
