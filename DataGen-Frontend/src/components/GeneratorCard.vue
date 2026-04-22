<template>
  <div class="bg-white p-7 rounded-2xl shadow-[0_4px_20px_rgba(0,0,0,0.04)] border border-gray-100 flex flex-col justify-between transition-transform hover:-translate-y-1 duration-300">
    <div>
      <div class="flex justify-between items-start mb-2">
        <h3 class="text-xl font-display font-semibold text-apple-dark-text tracking-tight">{{ gen.name }}</h3>
        <span class="text-[12px] bg-gray-100 text-gray-500 px-2.5 py-1 rounded-md font-medium tracking-wide">ID: {{ gen.id }}</span>
      </div>
      <p class="text-[15px] text-gray-500 leading-relaxed">{{ gen.description || 'No description provided.' }}</p>
    </div>
    
    <div class="mt-8">
      <div class="flex space-x-3 mb-5 pb-5 border-b border-gray-100">
        <button 
          @click="$emit('start', gen.id)" 
          class="flex-1 bg-[#34c759] text-white py-2.5 rounded-apple-pill hover:bg-[#2fb350] transition-colors text-[14px] font-medium flex items-center justify-center gap-1.5 shadow-sm"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
          </svg>
          Start
        </button>
        <button 
          @click="$emit('stop', gen.id)" 
          class="flex-1 bg-[#ff3b30] text-white py-2.5 rounded-apple-pill hover:bg-[#e6352b] transition-colors text-[14px] font-medium flex items-center justify-center gap-1.5 shadow-sm"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd" />
          </svg>
          Stop
        </button>
      </div>

      <div class="flex justify-between items-center">
        <router-link :to="`/generators/${gen.id}/nodes`" class="text-apple-link hover:text-apple-link-dark text-[14px] font-medium flex items-center gap-1 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Configure Nodes
        </router-link>
        <button @click="$emit('delete', gen.id)" class="text-gray-400 hover:text-[#ff3b30] text-[14px] font-medium transition-colors">
          Delete
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

// Accept the generator data from the parent view
defineProps({
  gen: {
    type: Object,
    required: true
  }
});

// Define the events this component can send up to the parent view
defineEmits(['start', 'stop', 'delete']);
</script>