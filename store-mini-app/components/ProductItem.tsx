
import React from 'react';
import { Product } from '../types';
import { useCart } from '../contexts/CartContext';
import { PlusIcon, MinusIcon } from './Icons';

interface ProductItemProps {
    product: Product;
}

const ProductItem: React.FC<ProductItemProps> = ({ product }) => {
    const { cartItems, addToCart, removeFromCart } = useCart();
    const itemInCart = cartItems.get(product.id);

    return (
        <div className="bg-secondary dark:bg-gray-700 rounded-lg shadow-md overflow-hidden flex items-stretch transition-transform hover:scale-105">
            <div className="relative w-1/3 flex-shrink-0">
                <div className="w-full" style={{ paddingTop: '100%' }} />
                <img
                    src={product.image}
                    alt={product.name}
                    className="absolute inset-0 w-full h-full object-cover"
                />
            </div>
            <div className="p-4 flex flex-col flex-grow w-2/3">
                <h3 className="text-lg font-semibold text-text">{product.name}</h3>
                <p className="text-sm text-hint mt-1 flex-grow">{product.description}</p>
                <div className="flex justify-between items-center mt-4">
                    <div className="text-text">
                        <span className="text-lg font-bold">${product.price.toFixed(2)}</span>
                        <span className="text-sm text-hint ml-2">/ {product.volume}</span>
                    </div>
                    {product.status === 'in_stock' ? (
                        <div className="flex items-center gap-2">
                            {itemInCart && itemInCart.quantity > 0 && (
                                <>
                                    <button onClick={() => removeFromCart(product.id)} className="p-2 rounded-full border border-primary bg-background text-primary hover:bg-primary hover:text-primary-text transition">
                                        <MinusIcon className="w-4 h-4" />
                                    </button>
                                    <span className="w-6 text-center font-bold text-lg text-text">{itemInCart.quantity}</span>
                                </>
                            )}
                            <button onClick={() => addToCart(product)} className="p-2 rounded-full bg-primary text-primary-text hover:opacity-80 transition">
                                <PlusIcon className="w-4 h-4" />
                            </button>
                        </div>
                    ) : (
                        <span className="text-sm font-semibold text-red-500 dark:text-red-400">Нет в наличии</span>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ProductItem;
