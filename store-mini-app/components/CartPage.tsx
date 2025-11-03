import React, { useEffect, useCallback } from 'react';
import { useCart } from '../contexts/CartContext';
import { useTelegram } from '../hooks/useTelegram';
import { BackIcon, TrashIcon, MinusIcon, PlusIcon } from './Icons';
import { CartItem } from '../types';

interface CartPageProps {
    setView: (view: 'products' | 'cart') => void;
}

const CartPage: React.FC<CartPageProps> = ({ setView }) => {
    const { cartItems, addToCart, removeFromCart, updateQuantity, totalItems, totalPrice } = useCart();
    const { tg } = useTelegram();

    const handleConfirmOrder = useCallback(() => {
        // FIX: Explicitly type 'item' to resolve property access errors.
        const orderData = Array.from(cartItems.values()).map((item: CartItem) => ({
            id: item.product.id,
            name: item.product.name,
            quantity: item.quantity,
            price: item.product.price
        }));

        if (orderData.length > 0) {
            tg.sendData(JSON.stringify({
                items: orderData,
                totalPrice: totalPrice.toFixed(2)
            }));
            tg.close();
        }
    }, [cartItems, tg, totalPrice]);
    
    useEffect(() => {
        if (totalItems > 0) {
            tg.MainButton.setText(`Оформить заказ ($${totalPrice.toFixed(2)})`);
            tg.MainButton.show();
            tg.MainButton.onClick(handleConfirmOrder);
        } else {
             tg.MainButton.hide();
        }

        return () => {
            tg.MainButton.offClick(handleConfirmOrder);
            tg.MainButton.hide();
        };
    }, [totalItems, totalPrice, tg, handleConfirmOrder]);

    const cartArray = Array.from(cartItems.values());

    return (
        <div className="p-4">
            <header className="flex items-center mb-6">
                <button onClick={() => setView('products')} className="p-2 mr-2 rounded-full hover:bg-secondary dark:hover:bg-gray-700">
                    <BackIcon className="w-6 h-6 text-text" />
                </button>
                <h1 className="text-3xl font-bold text-text">Корзина</h1>
            </header>
            {cartArray.length === 0 ? (
                <div className="text-center py-20">
                    <p className="text-hint text-lg">Ваша корзина пуста.</p>
                    <button onClick={() => setView('products')} className="mt-4 px-6 py-2 bg-primary text-primary-text rounded-lg font-semibold">
                        Перейти к покупкам
                    </button>
                </div>
            ) : (
                <div>
                    <div className="space-y-4">
                        {cartArray.map(({ product, quantity }) => (
                            <div key={product.id} className="flex items-center bg-secondary dark:bg-gray-700 p-3 rounded-lg">
                                <img src={product.image} alt={product.name} className="w-16 h-16 rounded-md object-cover mr-4" />
                                <div className="flex-grow">
                                    <h3 className="font-semibold text-text">{product.name}</h3>
                                    <p className="text-sm text-hint">${product.price.toFixed(2)}</p>
                                </div>
                                <div className="flex items-center gap-2">
                                     <button onClick={() => removeFromCart(product.id)} className="p-2 rounded-full border border-primary bg-background text-primary hover:bg-primary hover:text-primary-text transition">
                                        <MinusIcon className="w-4 h-4" />
                                    </button>
                                    <span className="w-6 text-center font-bold text-lg text-text">{quantity}</span>
                                    <button onClick={() => addToCart(product)} className="p-2 rounded-full bg-primary text-primary-text hover:opacity-80 transition">
                                        <PlusIcon className="w-4 h-4" />
                                    </button>
                                    <button onClick={() => updateQuantity(product.id, 0)} className="p-2 text-red-500 hover:text-red-700 dark:hover:text-red-400">
                                        <TrashIcon className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                    <div className="mt-8 pt-4 border-t border-gray-200 dark:border-gray-600">
                        <div className="flex justify-between text-lg font-bold text-text">
                            <span>Итого</span>
                            <span>${totalPrice.toFixed(2)}</span>
                        </div>
                        <p className="text-right text-hint text-sm mt-1">{totalItems} шт.</p>
                         <div className="mt-6">
                            <button
                                onClick={handleConfirmOrder}
                                className="w-full py-3 bg-primary text-primary-text rounded-xl shadow-lg hover:opacity-90 transition-opacity font-semibold text-lg"
                            >
                                Оформить заказ
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CartPage;
